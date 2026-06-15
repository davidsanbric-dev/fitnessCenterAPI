from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain import MembershipStatus
from app.models import (
    MemberMembership,
    MembershipPlan,
    membership_plan_categories,
    trainer_membership_plans,
)


# Adapted repository around clinic prevision concept promoted as gym MembershipPlan entity.
class MembershipRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_plans(self) -> list[MembershipPlan]:
        statement = select(MembershipPlan).options(selectinload(MembershipPlan.allowed_categories)).order_by(MembershipPlan.price)
        return list(self.db.scalars(statement).all())

    def get_plan(self, plan_id: int) -> MembershipPlan | None:
        statement = select(MembershipPlan).options(selectinload(MembershipPlan.allowed_categories)).where(MembershipPlan.id == plan_id)
        return self.db.scalar(statement)

    def get_user_membership(self, user_id: int) -> MemberMembership | None:
        statement = select(MemberMembership).options(selectinload(MemberMembership.plan).selectinload(MembershipPlan.allowed_categories)).where(MemberMembership.user_id == user_id)
        return self.db.scalar(statement)

    def get_by_name(self, name: str) -> MembershipPlan | None:
        return self.db.scalar(select(MembershipPlan).where(MembershipPlan.name == name))

    def get_default_plan(self) -> MembershipPlan | None:
        # The cheapest plan is treated as the default ("basic") plan assigned at
        # registration.
        return self.db.scalar(select(MembershipPlan).order_by(MembershipPlan.price))

    def create_default_membership(self, user_id: int, plan: MembershipPlan) -> MemberMembership:
        # Provisions a fresh active membership on the given plan, running from
        # today through the plan's duration. Used when a member is registered.
        today = date.today()
        membership = MemberMembership(
            user_id=user_id,
            membership_plan_id=plan.id,
            start_date=today,
            end_date=today + timedelta(days=plan.duration_days),
            status=MembershipStatus.ACTIVE,
            bookings_used=0,
        )
        self.db.add(membership)
        self.db.commit()
        self.db.refresh(membership)
        return membership

    def create_plan(self, plan: MembershipPlan) -> MembershipPlan:
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def update_plan(self, plan: MembershipPlan, payload: dict) -> MembershipPlan:
        for field, value in payload.items():
            setattr(plan, field, value)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def has_dependencies(self, plan_id: int) -> bool:
        member_links = int(
            self.db.scalar(
                select(func.count()).select_from(MemberMembership).where(MemberMembership.membership_plan_id == plan_id)
            )
            or 0
        )
        trainer_links = int(
            self.db.scalar(
                select(func.count()).select_from(trainer_membership_plans).where(
                    trainer_membership_plans.c.membership_plan_id == plan_id
                )
            )
            or 0
        )
        category_links = int(
            self.db.scalar(
                select(func.count()).select_from(membership_plan_categories).where(
                    membership_plan_categories.c.membership_plan_id == plan_id
                )
            )
            or 0
        )
        return (member_links + trainer_links + category_links) > 0

    def delete_plan(self, plan: MembershipPlan) -> None:
        self.db.delete(plan)
        self.db.commit()

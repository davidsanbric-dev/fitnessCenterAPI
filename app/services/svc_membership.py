from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import MembershipPlan
from app.repositories.rps_membership import MembershipRepository
from app.services.svc_common import serialize_membership


# Adapted service from clinic prevision filtering concept to gym membership management reads.
class MembershipService:
    def __init__(self, db: Session):
        self.repository = MembershipRepository(db)

    def list_plans(self) -> dict:
        plans = self.repository.list_plans()
        return {
            "items": [
                {
                    "membership_plan_id": plan.id,
                    "name": plan.name,
                    "description": plan.description,
                    "price": plan.price,
                    "duration_days": plan.duration_days,
                    "features": plan.features,
                    "max_bookings_per_month": plan.max_bookings_per_month,
                    "includes_personal_training": plan.includes_personal_training,
                }
                for plan in plans
            ]
        }

    def get_plan(self, plan_id: int) -> dict:
        plan = self.repository.get_plan(plan_id)
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership plan not found")
        return {
            "membership_plan_id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "price": plan.price,
            "duration_days": plan.duration_days,
            "features": plan.features,
            "max_bookings_per_month": plan.max_bookings_per_month,
            "includes_personal_training": plan.includes_personal_training,
            "allowed_class_categories": [
                {"category_id": category.id, "name": category.name}
                for category in plan.allowed_categories
            ],
        }

    def get_current_membership(self, user_id: int) -> dict:
        membership = self.repository.get_user_membership(user_id)
        if membership is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
        return serialize_membership(membership)

    def create_plan(self, payload) -> dict:
        if self.repository.get_by_name(payload.name):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Membership plan name already exists")

        plan = self.repository.create_plan(
            MembershipPlan(
                name=payload.name,
                description=payload.description,
                price=payload.price,
                duration_days=payload.duration_days,
                features=payload.features,
                max_bookings_per_month=payload.max_bookings_per_month,
                includes_personal_training=payload.includes_personal_training,
            )
        )
        return {
            "membership_plan_id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "price": plan.price,
            "duration_days": plan.duration_days,
            "features": plan.features,
            "max_bookings_per_month": plan.max_bookings_per_month,
            "includes_personal_training": plan.includes_personal_training,
        }

    def update_plan(self, plan_id: int, payload) -> dict:
        plan = self.repository.get_plan(plan_id)
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership plan not found")

        if payload.name != plan.name and self.repository.get_by_name(payload.name):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Membership plan name already exists")

        updated = self.repository.update_plan(
            plan,
            {
                "name": payload.name,
                "description": payload.description,
                "price": payload.price,
                "duration_days": payload.duration_days,
                "features": payload.features,
                "max_bookings_per_month": payload.max_bookings_per_month,
                "includes_personal_training": payload.includes_personal_training,
            },
        )
        return {
            "membership_plan_id": updated.id,
            "name": updated.name,
            "description": updated.description,
            "price": updated.price,
            "duration_days": updated.duration_days,
            "features": updated.features,
            "max_bookings_per_month": updated.max_bookings_per_month,
            "includes_personal_training": updated.includes_personal_training,
        }

    def delete_plan(self, plan_id: int) -> dict:
        plan = self.repository.get_plan(plan_id)
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership plan not found")

        if self.repository.has_dependencies(plan_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete membership plan with active references",
            )

        self.repository.delete_plan(plan)
        return {"message": "Membership plan deleted"}

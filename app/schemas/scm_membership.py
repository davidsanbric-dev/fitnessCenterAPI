from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from app.schemas import APIModel

if TYPE_CHECKING:
    from app.models import MemberMembership, MembershipPlan


def _plan_fields(plan: MembershipPlan) -> dict:
    # Shared mapping for the plan node, reused by the plain and detail responses.
    return {
        "membership_plan_id": plan.id,
        "name": plan.name,
        "description": plan.description,
        "price": plan.price,
        "duration_days": plan.duration_days,
        "features": plan.features,
        "max_bookings_per_month": plan.max_bookings_per_month,
    }


# Adapted from clinic Prevision filter concept -> gym MembershipPlan payload.
class MembershipPlanResponse(APIModel):
    membership_plan_id: int
    name: str
    description: str | None = None
    price: Decimal
    duration_days: int
    features: list[str]
    max_bookings_per_month: int

    @classmethod
    def from_model(cls, plan: MembershipPlan) -> MembershipPlanResponse:
        return cls(**_plan_fields(plan))


class MembershipPlanDetailResponse(MembershipPlanResponse):
    # Gym expansion of adapted prevision entity with allowed categories.
    allowed_class_categories: list[dict]

    @classmethod
    def from_model(cls, plan: MembershipPlan) -> MembershipPlanDetailResponse:
        return cls(
            **_plan_fields(plan),
            allowed_class_categories=[
                {"category_id": category.id, "name": category.name}
                for category in plan.allowed_categories
            ],
        )


class CurrentMembershipResponse(APIModel):
    # Member-plan relation derived from adapted prevision semantics.
    plan: MembershipPlanResponse
    start_date: date
    end_date: date
    status: str
    bookings_used: int
    bookings_remaining: int

    @classmethod
    def from_model(cls, membership: MemberMembership) -> CurrentMembershipResponse:
        remaining = max(membership.plan.max_bookings_per_month - membership.bookings_used, 0)
        return cls(
            plan=MembershipPlanResponse.from_model(membership.plan),
            start_date=membership.start_date,
            end_date=membership.end_date,
            status=membership.status,
            bookings_used=membership.bookings_used,
            bookings_remaining=remaining,
        )


class AdminMembershipPlanUpsertRequest(APIModel):
    name: str
    description: str | None = None
    price: Decimal
    duration_days: int
    features: list[str]
    max_bookings_per_month: int

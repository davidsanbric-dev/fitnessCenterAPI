from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.schemas import APIModel


# Adapted from clinic Prevision filter concept -> gym MembershipPlan payload.
class MembershipPlanResponse(APIModel):
    membership_plan_id: int
    name: str
    description: str | None = None
    price: Decimal
    duration_days: int
    features: list[str]
    max_bookings_per_month: int
    includes_personal_training: bool


class MembershipPlanDetailResponse(MembershipPlanResponse):
    # Gym expansion of adapted prevision entity with allowed categories.
    allowed_class_categories: list[dict]


class CurrentMembershipResponse(APIModel):
    # Member-plan relation derived from adapted prevision semantics.
    plan: MembershipPlanResponse
    start_date: date
    end_date: date
    status: str
    bookings_used: int
    bookings_remaining: int


class AdminMembershipPlanUpsertRequest(APIModel):
    name: str
    description: str | None = None
    price: Decimal
    duration_days: int
    features: list[str]
    max_bookings_per_month: int
    includes_personal_training: bool

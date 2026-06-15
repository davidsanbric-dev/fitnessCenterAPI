from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from pydantic import EmailStr

from app.schemas import APIModel

if TYPE_CHECKING:
    from app.models import User


# Adapted from clinic Prevision reference -> embedded gym MembershipPlan summary.
class MembershipPlanEmbedded(APIModel):
    membership_plan_id: int
    name: str
    description: str | None = None


class CurrentUserResponse(APIModel):
    # Adapted from clinic GetPatientDTO -> gym current member profile response.
    id: int
    email: EmailStr
    first_name: str
    paternal_surname: str
    maternal_surname: str
    rut: str | None = None
    mobile_phone: str
    landline_phone: str | None = None
    birth_date: date | None = None
    address: str | None = None
    avatar_url: str | None = None
    membership_plan: MembershipPlanEmbedded | None = None
    fitness_goals: str | None = None
    created_at: datetime

    @classmethod
    def from_model(cls, user: User) -> CurrentUserResponse:
        # Profile is required for this projection (callers guarantee it exists).
        profile = user.profile
        membership_plan = None
        if user.membership and user.membership.plan:
            plan = user.membership.plan
            membership_plan = MembershipPlanEmbedded(
                membership_plan_id=plan.id,
                name=plan.name,
                description=plan.description,
            )
        return cls(
            id=user.id,
            email=user.email,
            first_name=profile.first_name,
            paternal_surname=profile.paternal_surname,
            maternal_surname=profile.maternal_surname,
            rut=profile.rut,
            mobile_phone=profile.mobile_phone,
            landline_phone=profile.landline_phone,
            birth_date=profile.birth_date,
            address=profile.address,
            avatar_url=profile.avatar_url,
            membership_plan=membership_plan,
            fitness_goals=profile.fitness_goals,
            created_at=user.created_at,
        )


class UpdateUserRequest(APIModel):
    # Adapted from clinic patient update semantics -> gym member profile update payload.
    first_name: str | None = None
    paternal_surname: str | None = None
    maternal_surname: str | None = None
    mobile_phone: str | None = None
    landline_phone: str | None = None
    birth_date: date | None = None
    address: str | None = None
    avatar_url: str | None = None
    fitness_goals: str | None = None

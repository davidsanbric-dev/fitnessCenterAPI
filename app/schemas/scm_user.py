from __future__ import annotations

from datetime import date, datetime

from pydantic import EmailStr

from app.schemas import APIModel


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

from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.schemas import APIModel


# Adapted from clinic ProfessionalDTO projection -> gym trainer list item.
class TrainerSummary(APIModel):
    trainer_id: int
    full_name: str
    discipline_id: int | None = None
    discipline_name: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    certifications: list[str] = []


class TrainerAvailabilityItem(APIModel):
    # Adapted from clinic available appointment slot data for a professional.
    slot_datetime: datetime
    location_id: int | None = None
    is_available: bool
    discipline_name: str | None = None


class TrainerAvailabilityResponse(APIModel):
    # Adapted trainer availability envelope for gym domain.
    trainer_id: int
    slots: list[TrainerAvailabilityItem]


class TrainerDetailResponse(APIModel):
    # Adapted trainer detail combining clinic professional identity with gym enrichments.
    trainer_id: int
    trainer_code: int
    full_name: str
    bio: str | None = None
    photo_url: str | None = None
    certifications: list[str] = []
    disciplines: list[dict]
    upcoming_availability: list[TrainerAvailabilityItem]


# ---- Trainer self-service ("me") schemas --------------------------------------
# Drive the web modules a signed-in trainer is scoped to: profile, slots, home.


class TrainerMeProfileResponse(APIModel):
    trainer_id: int
    trainer_code: int
    full_name: str
    email: str
    bio: str | None = None
    photo_url: str | None = None
    certifications: list[str] = []
    location_id: int | None = None
    disciplines: list[dict] = []


class TrainerAdminCreateRequest(APIModel):
    # Admin-web staff trainer provisioning: credentials (Firebase account) plus the
    # trainer's personal data. The account is created email-verified (showcase), so
    # the new trainer can sign in to the web app immediately.
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=1, max_length=150)
    bio: str | None = None
    photo_url: str | None = None
    certifications: list[str] = []
    discipline_id: int | None = None

    @field_validator("certifications", mode="before")
    @classmethod
    def _split_certifications(cls, value: object) -> object:
        # Accept either a real list (API clients) or a comma-separated string. The
        # admin-web CRUD form sends only scalar fields, so it passes a CSV string.
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class TrainerMeProfileUpdate(APIModel):
    # All optional: a trainer can edit any subset of its editable personal data.
    full_name: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    certifications: list[str] | None = None


class TrainerSlotResponse(APIModel):
    slot_id: int
    slot_datetime: datetime
    location_id: int | None = None
    discipline_id: int | None = None
    discipline_name: str | None = None
    is_available: bool
    slot_assignment_code: str | None = None
    schedule_type: str | None = None


class TrainerSlotCreate(APIModel):
    slot_datetime: datetime
    discipline_id: int | None = None
    schedule_type: str | None = "PERSONAL"


class TrainerSlotUpdate(APIModel):
    slot_datetime: datetime | None = None
    is_available: bool | None = None


class TrainerDashboardResponse(APIModel):
    trainer: dict
    kpis: dict
    upcoming_slots: list[TrainerSlotResponse]

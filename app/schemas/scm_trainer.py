from __future__ import annotations

from datetime import datetime

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

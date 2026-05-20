from __future__ import annotations

from datetime import datetime

from app.schemas import APIModel


# Adapted from clinic Specialty entity -> gym Discipline summary.
class DisciplineSummary(APIModel):
    discipline_id: int
    discipline_code: str
    name: str
    description: str | None = None
    icon_url: str | None = None
    trainers_count: int = 0


class DisciplineTrainerSummary(APIModel):
    # Adapted clinic professional-by-specialty projection.
    trainer_id: int
    full_name: str
    bio: str | None = None
    photo_url: str | None = None


class DisciplineAvailabilityTrainer(APIModel):
    # Adapted professional node inside availability responses.
    trainer_id: int
    full_name: str
    discipline_id: int | None = None
    discipline_name: str | None = None


class DisciplineAvailabilityItem(APIModel):
    # Adapted slot shape from clinic GetAvailableAppointments.
    slot_datetime: datetime
    location_id: int | None = None
    is_online: bool
    trainer: DisciplineAvailabilityTrainer


class DisciplineDetailResponse(APIModel):
    # Adapted discipline detail equivalent of clinic specialty + associated professionals.
    discipline_id: int
    discipline_code: str
    name: str
    description: str | None = None
    icon_url: str | None = None
    trainers: list[DisciplineTrainerSummary]


class DisciplineAvailabilityResponse(APIModel):
    # Adapted availability envelope for discipline-level queries.
    discipline_id: int
    slots: list[DisciplineAvailabilityItem]

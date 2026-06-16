from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from pydantic import EmailStr, Field, field_validator

from app.schemas import APIModel

if TYPE_CHECKING:
    from app.models import Discipline, Slot, Trainer


class TrainerDisciplineInfo(APIModel):
    # Discipline node shared by the trainer detail and self-profile projections.
    discipline_id: int
    discipline_code: str | None = None
    discipline_name: str

    @classmethod
    def from_model(cls, discipline: Discipline) -> TrainerDisciplineInfo:
        return cls(
            discipline_id=discipline.id,
            discipline_code=discipline.discipline_code,
            discipline_name=discipline.name,
        )


# Adapted from clinic ProfessionalDTO projection -> gym trainer list item.
class TrainerSummary(APIModel):
    trainer_id: int
    full_name: str
    discipline_id: int | None = None
    discipline_name: str | None = None
    location_id: int | None = None
    location_name: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    certifications: list[str] = []

    @classmethod
    def from_model(cls, trainer: Trainer) -> TrainerSummary:
        discipline = trainer.disciplines[0] if trainer.disciplines else None
        return cls(
            trainer_id=trainer.id,
            full_name=trainer.full_name,
            discipline_id=discipline.id if discipline else None,
            discipline_name=discipline.name if discipline else None,
            location_id=trainer.location_id,
            location_name=trainer.location.name if trainer.location else None,
            bio=trainer.bio,
            photo_url=trainer.photo_url,
            certifications=trainer.certifications or [],
        )


class TrainerAvailabilityItem(APIModel):
    # Adapted from clinic available appointment slot data for a professional.
    slot_datetime: datetime
    location_id: int | None = None
    is_available: bool
    discipline_name: str | None = None

    @classmethod
    def from_slot(cls, slot: Slot) -> TrainerAvailabilityItem:
        return cls(
            slot_datetime=slot.slot_datetime,
            location_id=slot.location_id,
            is_available=slot.is_available,
            discipline_name=slot.discipline.name if slot.discipline else None,
        )


class TrainerAvailabilityResponse(APIModel):
    # Adapted trainer availability envelope for gym domain.
    trainer_id: int
    slots: list[TrainerAvailabilityItem]

    @classmethod
    def from_slots(cls, trainer_id: int, slots: list[Slot]) -> TrainerAvailabilityResponse:
        return cls(trainer_id=trainer_id, slots=[TrainerAvailabilityItem.from_slot(slot) for slot in slots])


class TrainerDetailResponse(APIModel):
    # Adapted trainer detail combining clinic professional identity with gym enrichments.
    trainer_id: int
    trainer_code: int
    full_name: str
    bio: str | None = None
    photo_url: str | None = None
    certifications: list[str] = []
    disciplines: list[TrainerDisciplineInfo]
    upcoming_availability: list[TrainerAvailabilityItem]

    @classmethod
    def from_model(cls, trainer: Trainer) -> TrainerDetailResponse:
        # Public detail view: only the next two weeks of availability are surfaced.
        now = datetime.utcnow()
        horizon = now + timedelta(days=14)
        upcoming = [
            TrainerAvailabilityItem.from_slot(slot)
            for slot in trainer.slots
            if now <= slot.slot_datetime <= horizon
        ]
        return cls(
            trainer_id=trainer.id,
            trainer_code=trainer.trainer_code,
            full_name=trainer.full_name,
            bio=trainer.bio,
            photo_url=trainer.photo_url,
            certifications=trainer.certifications or [],
            disciplines=[TrainerDisciplineInfo.from_model(discipline) for discipline in trainer.disciplines],
            upcoming_availability=upcoming,
        )


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
    disciplines: list[TrainerDisciplineInfo] = []

    @classmethod
    def from_trainer(cls, trainer: Trainer, email: str) -> TrainerMeProfileResponse:
        # Email is sourced from the linked user account, not the Trainer record.
        return cls(
            trainer_id=trainer.id,
            trainer_code=trainer.trainer_code,
            full_name=trainer.full_name,
            email=email,
            bio=trainer.bio,
            photo_url=trainer.photo_url,
            certifications=trainer.certifications or [],
            location_id=trainer.location_id,
            disciplines=[TrainerDisciplineInfo.from_model(discipline) for discipline in trainer.disciplines],
        )


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

    @classmethod
    def from_model(cls, slot: Slot) -> TrainerSlotResponse:
        return cls(
            slot_id=slot.id,
            slot_datetime=slot.slot_datetime,
            location_id=slot.location_id,
            discipline_id=slot.discipline_id,
            discipline_name=slot.discipline.name if slot.discipline else None,
            is_available=slot.is_available,
            slot_assignment_code=slot.slot_assignment_code,
            schedule_type=slot.schedule_type,
        )


class TrainerSlotCreate(APIModel):
    slot_datetime: datetime
    discipline_id: int | None = None
    schedule_type: str | None = "PERSONAL"


class TrainerSlotUpdate(APIModel):
    slot_datetime: datetime | None = None
    is_available: bool | None = None


class TrainerDashboardTrainer(APIModel):
    # Identity header for the signed-in trainer's dashboard.
    trainer_id: int
    full_name: str
    trainer_code: int

    @classmethod
    def from_model(cls, trainer: Trainer) -> TrainerDashboardTrainer:
        return cls(trainer_id=trainer.id, full_name=trainer.full_name, trainer_code=trainer.trainer_code)


class TrainerDashboardKpis(APIModel):
    # Slot counters derived from the trainer's full slot list.
    total_slots: int
    available_slots: int
    upcoming_slots: int
    booked_slots: int


class TrainerDashboardResponse(APIModel):
    trainer: TrainerDashboardTrainer
    kpis: TrainerDashboardKpis
    upcoming_slots: list[TrainerSlotResponse]

    @classmethod
    def build(cls, trainer: Trainer, slots: list[Slot]) -> TrainerDashboardResponse:
        # Owns the "now" window and the slot aggregation; the service only fetches.
        now = datetime.utcnow()
        upcoming = [slot for slot in slots if slot.slot_datetime >= now]
        return cls(
            trainer=TrainerDashboardTrainer.from_model(trainer),
            kpis=TrainerDashboardKpis(
                total_slots=len(slots),
                available_slots=sum(1 for slot in slots if slot.is_available),
                upcoming_slots=len(upcoming),
                booked_slots=sum(1 for slot in slots if not slot.is_available),
            ),
            upcoming_slots=[TrainerSlotResponse.from_model(slot) for slot in upcoming[:5]],
        )

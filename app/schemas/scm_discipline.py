from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.schemas import APIModel

if TYPE_CHECKING:
    from app.models import Discipline, Slot, Trainer


# Adapted from clinic Specialty entity -> gym Discipline summary.
class DisciplineSummary(APIModel):
    discipline_id: int
    discipline_code: str
    name: str
    description: str | None = None
    icon_url: str | None = None
    trainers_count: int = 0
    # Populated when the listing is scoped to a club so the mobile directory can
    # render the discipline name above its offering location.
    location_id: int | None = None
    location_name: str | None = None

    @classmethod
    def from_model(
        cls,
        discipline: Discipline,
        location_id: int | None = None,
        location_name: str | None = None,
    ) -> DisciplineSummary:
        return cls(
            discipline_id=discipline.id,
            discipline_code=discipline.discipline_code,
            name=discipline.name,
            description=discipline.description,
            icon_url=discipline.icon_url,
            trainers_count=len(discipline.trainers),
            location_id=location_id,
            location_name=location_name,
        )


class DisciplineTrainerSummary(APIModel):
    # Adapted clinic professional-by-specialty projection.
    trainer_id: int
    full_name: str
    bio: str | None = None
    photo_url: str | None = None

    @classmethod
    def from_model(cls, trainer: Trainer) -> DisciplineTrainerSummary:
        return cls(
            trainer_id=trainer.id,
            full_name=trainer.full_name,
            bio=trainer.bio,
            photo_url=trainer.photo_url,
        )


class DisciplineAvailabilityTrainer(APIModel):
    # Adapted professional node inside availability responses.
    trainer_id: int
    full_name: str
    discipline_id: int | None = None
    discipline_name: str | None = None

    @classmethod
    def from_slot(cls, slot: Slot) -> DisciplineAvailabilityTrainer:
        # Built only for slots that have a trainer; discipline comes from the slot.
        return cls(
            trainer_id=slot.trainer.id,
            full_name=slot.trainer.full_name,
            discipline_id=slot.discipline.id if slot.discipline else None,
            discipline_name=slot.discipline.name if slot.discipline else None,
        )


class DisciplineAvailabilityItem(APIModel):
    # Adapted slot shape from clinic GetAvailableAppointments.
    slot_datetime: datetime
    location_id: int | None = None
    trainer: DisciplineAvailabilityTrainer

    @classmethod
    def from_slot(cls, slot: Slot) -> DisciplineAvailabilityItem:
        return cls(
            slot_datetime=slot.slot_datetime,
            location_id=slot.location_id,
            trainer=DisciplineAvailabilityTrainer.from_slot(slot),
        )


class DisciplineDetailResponse(APIModel):
    # Adapted discipline detail equivalent of clinic specialty + associated professionals.
    discipline_id: int
    discipline_code: str
    name: str
    description: str | None = None
    icon_url: str | None = None
    trainers: list[DisciplineTrainerSummary]

    @classmethod
    def from_model(cls, discipline: Discipline) -> DisciplineDetailResponse:
        return cls(
            discipline_id=discipline.id,
            discipline_code=discipline.discipline_code,
            name=discipline.name,
            description=discipline.description,
            icon_url=discipline.icon_url,
            trainers=[DisciplineTrainerSummary.from_model(trainer) for trainer in discipline.trainers],
        )


class DisciplineAvailabilityResponse(APIModel):
    # Adapted availability envelope for discipline-level queries.
    discipline_id: int
    slots: list[DisciplineAvailabilityItem]

    @classmethod
    def from_slots(cls, discipline_id: int, slots: list[Slot]) -> DisciplineAvailabilityResponse:
        return cls(
            discipline_id=discipline_id,
            slots=[DisciplineAvailabilityItem.from_slot(slot) for slot in slots if slot.trainer is not None],
        )

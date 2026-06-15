from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.schemas import APIModel

if TYPE_CHECKING:
    from app.models import Slot


# Adapted professional node from clinic availability DTOs.
class SlotTrainerInfo(APIModel):
    trainer_id: int
    trainer_code: int | None = None
    full_name: str
    discipline_id: int | None = None
    discipline_code: str | None = None
    discipline_name: str | None = None

    @classmethod
    def from_slot(cls, slot: Slot) -> SlotTrainerInfo:
        # Prefer the trainer's primary discipline, else the slot's own discipline.
        discipline = slot.trainer.disciplines[0] if slot.trainer.disciplines else slot.discipline
        return cls(
            trainer_id=slot.trainer.id,
            trainer_code=slot.trainer.trainer_code,
            full_name=slot.trainer.full_name,
            discipline_id=discipline.id if discipline else None,
            discipline_code=discipline.discipline_code if discipline else None,
            discipline_name=discipline.name if discipline else None,
        )


class SlotResponse(APIModel):
    # Unified adapted slot projection (appointments + service appointments).
    slot_datetime: datetime
    location_id: int | None = None
    slot_assignment_code: str | None = None
    schedule_type: str | None = None
    is_available: bool
    trainer: SlotTrainerInfo | None = None

    @classmethod
    def from_model(cls, slot: Slot) -> SlotResponse:
        return cls(
            slot_datetime=slot.slot_datetime,
            location_id=slot.location_id,
            slot_assignment_code=slot.slot_assignment_code,
            schedule_type=slot.schedule_type,
            is_available=slot.is_available,
            trainer=SlotTrainerInfo.from_slot(slot) if slot.trainer else None,
        )

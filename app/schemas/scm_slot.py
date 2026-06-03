from __future__ import annotations

from datetime import datetime

from app.schemas import APIModel


# Adapted professional node from clinic availability DTOs.
class SlotTrainerInfo(APIModel):
    trainer_id: int
    trainer_code: int | None = None
    full_name: str
    discipline_id: int | None = None
    discipline_code: str | None = None
    discipline_name: str | None = None


class SlotResponse(APIModel):
    # Unified adapted slot projection (appointments + service appointments).
    slot_datetime: datetime
    location_id: int | None = None
    slot_assignment_code: str | None = None
    schedule_type: str | None = None
    is_available: bool
    trainer: SlotTrainerInfo | None = None

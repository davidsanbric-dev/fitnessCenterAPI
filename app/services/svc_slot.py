from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.domain import ScheduleType
from app.models import Slot, Trainer
from app.repositories.rps_slot import SlotRepository
from app.schemas import PaginatedResponse
from app.schemas.scm_slot import SlotResponse


class SlotService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = SlotRepository(db)

    def search_slots(self, **filters) -> PaginatedResponse[SlotResponse]:
        items, total = self.repository.search_slots(**filters)
        return PaginatedResponse[SlotResponse].build(
            items=[SlotResponse.from_model(item) for item in items],
            total=total,
            page=filters["page"],
            page_size=filters["page_size"],
        )

    def get_availability_by_trainer(
        self,
        trainer_id: int,
        date_from: datetime,
        date_to: datetime,
        discipline_id: int | None = None,
    ) -> list[Slot]:
        return self.repository.get_availability_by_trainer(trainer_id, date_from, date_to, discipline_id)

    def list_for_trainer(self, trainer_id: int) -> list[Slot]:
        return self.repository.list_for_trainer(trainer_id)

    def get_slot(self, slot_id: int) -> Slot | None:
        return self.repository.get_slot(slot_id)

    def require_own_slot(self, trainer_id: int, slot_id: int) -> Slot:
        slot = self.repository.get_slot(slot_id)
        if slot is None or slot.trainer_id != trainer_id:
            raise NotFoundException("Slot not found")
        return slot

    def create_slot(self, trainer: Trainer, payload: dict) -> Slot:
        slot = Slot(
            slot_datetime=payload["slot_datetime"],
            location_id=trainer.location_id,
            trainer_id=trainer.id,
            discipline_id=payload.get("discipline_id"),
            is_available=True,
            schedule_type=payload.get("schedule_type") or ScheduleType.PERSONAL,
        )
        return self.repository.create_slot(slot)

    def update_slot(self, slot: Slot, payload: dict) -> Slot:
        return self.repository.update_slot(slot, payload)

    def delete_slot(self, slot: Slot) -> None:
        self.repository.delete_slot(slot)

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    ClassType,
    Discipline,
    Location,
    Slot,
    Trainer,
)


# Adapted unified repository over clinic GetAvailableAppointments and GetAvailableServiceAppointments.
class SlotRepository:
    def __init__(self, db: Session):
        self.db = db

    def search_slots(
        self,
        date_from: datetime,
        date_to: datetime,
        location_code: str | None = None,
        trainer_id: int | None = None,
        discipline_id: int | None = None,
        discipline_code: str | None = None,
        class_type_id: int | None = None,
        query_type: str | None = None,
        session_duration_minutes: int | None = None,
        is_online: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Slot], int]:
        # Adapted dual-path slot search: discipline path (A) and class-type path (B).
        statement = (
            select(Slot)
            .options(selectinload(Slot.trainer).selectinload(Trainer.disciplines), selectinload(Slot.location))
            .where(
                Slot.slot_datetime >= date_from,
                Slot.slot_datetime <= date_to,
                Slot.is_available.is_(True),
            )
        )
        count_statement = select(func.count()).select_from(Slot).where(
            Slot.slot_datetime >= date_from,
            Slot.slot_datetime <= date_to,
            Slot.is_available.is_(True),
        )
        if location_code is not None:
            statement = statement.join(Slot.location).where(Location.location_code == location_code)
            count_statement = count_statement.join(Slot.location).where(Location.location_code == location_code)
        if trainer_id is not None:
            statement = statement.where(Slot.trainer_id == trainer_id)
            count_statement = count_statement.where(Slot.trainer_id == trainer_id)
        if discipline_id is not None:
            statement = statement.where(Slot.discipline_id == discipline_id)
            count_statement = count_statement.where(Slot.discipline_id == discipline_id)
        elif discipline_code is not None:
            statement = statement.join(Slot.discipline).where(Discipline.discipline_code == discipline_code)
            count_statement = count_statement.join(Slot.discipline).where(Discipline.discipline_code == discipline_code)
        if class_type_id is not None:
            statement = statement.join(Slot.class_type).where(ClassType.id == class_type_id)
            count_statement = count_statement.join(Slot.class_type).where(ClassType.id == class_type_id)
        if is_online is not None:
            statement = statement.where(Slot.is_online == is_online)
            count_statement = count_statement.where(Slot.is_online == is_online)
        if query_type == "2" and trainer_id is None:
            return [], 0
        items = self.db.scalars(statement.order_by(Slot.slot_datetime).offset((page - 1) * page_size).limit(page_size)).all()
        total = int(self.db.scalar(count_statement) or 0)
        return list(items), total

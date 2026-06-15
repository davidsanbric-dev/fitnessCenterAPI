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
        if query_type == "2" and trainer_id is None:
            return [], 0
        items = self.db.scalars(statement.order_by(Slot.slot_datetime).offset((page - 1) * page_size).limit(page_size)).all()
        total = int(self.db.scalar(count_statement) or 0)
        return list(items), total

    def get_availability_by_discipline(
        self,
        discipline_id: int,
        date_from: datetime,
        date_to: datetime,
        trainer_id: int | None = None,
        location_code: str | None = None,
    ) -> list[Slot]:
        # Adapted from clinic specialty slot search window.
        statement = (
            select(Slot)
            .options(selectinload(Slot.trainer).selectinload(Trainer.disciplines))
            .where(
                Slot.discipline_id == discipline_id,
                Slot.slot_datetime >= date_from,
                Slot.slot_datetime <= date_to,
                Slot.is_available.is_(True),
            )
        )
        if trainer_id is not None:
            statement = statement.where(Slot.trainer_id == trainer_id)
        if location_code is not None:
            statement = statement.join(Slot.location).where(Location.location_code == location_code)
        return list(self.db.scalars(statement.order_by(Slot.slot_datetime)).all())

    def get_availability_by_trainer(
        self,
        trainer_id: int,
        date_from: datetime,
        date_to: datetime,
        discipline_id: int | None = None,
    ) -> list[Slot]:
        # Adapted from clinic GetAvailableAppointments for a specific professional.
        statement = (
            select(Slot)
            .options(selectinload(Slot.discipline))
            .where(
                Slot.trainer_id == trainer_id,
                Slot.slot_datetime >= date_from,
                Slot.slot_datetime <= date_to,
                Slot.is_available.is_(True),
            )
        )
        if discipline_id is not None:
            statement = statement.where(Slot.discipline_id == discipline_id)
        return list(self.db.scalars(statement.order_by(Slot.slot_datetime)).all())

    # ---- trainer-owned slot management ---------------------------------------

    def list_for_trainer(self, trainer_id: int) -> list[Slot]:
        statement = (
            select(Slot)
            .options(selectinload(Slot.discipline))
            .where(Slot.trainer_id == trainer_id)
            .order_by(Slot.slot_datetime)
        )
        return list(self.db.scalars(statement).all())

    def get_slot(self, slot_id: int) -> Slot | None:
        statement = (
            select(Slot)
            .options(selectinload(Slot.discipline))
            .where(Slot.id == slot_id)
        )
        return self.db.scalar(statement)

    def create_slot(self, slot: Slot) -> Slot:
        self.db.add(slot)
        self.db.commit()
        self.db.refresh(slot)
        return slot

    def update_slot(self, slot: Slot, fields: dict) -> Slot:
        for key in ("slot_datetime", "is_available"):
            if key in fields and fields[key] is not None:
                setattr(slot, key, fields[key])
        self.db.commit()
        self.db.refresh(slot)
        return slot

    def delete_slot(self, slot: Slot) -> None:
        self.db.delete(slot)
        self.db.commit()

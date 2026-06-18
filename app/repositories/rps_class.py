from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    ClassCategory,
    ClassSubcategory,
    ClassType,
    Slot,
    Trainer,
)


# Adapted repository from clinic GetCapabilities hierarchy and service availability contracts.
class ClassRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_categories(self) -> list[ClassCategory]:
        # Adapted TipoConsulta="1" (groups) query.
        statement = select(ClassCategory).options(selectinload(ClassCategory.subcategories))
        return list(self.db.scalars(statement.order_by(ClassCategory.name)).all())

    def list_subcategories(self, category_id: int) -> list[ClassSubcategory]:
        # Adapted TipoConsulta="2" (subgroups) query.
        statement = select(ClassSubcategory).options(selectinload(ClassSubcategory.class_types)).where(ClassSubcategory.category_id == category_id)
        return list(self.db.scalars(statement.order_by(ClassSubcategory.name)).all())

    def list_class_types(self, subcategory_id: int) -> list[ClassType]:
        # Adapted TipoConsulta="3" (services/class types) query.
        statement = select(ClassType).where(ClassType.subcategory_id == subcategory_id)
        return list(self.db.scalars(statement.order_by(ClassType.name)).all())

    def get_class_type(self, class_type_id: int) -> ClassType | None:
        statement = (
            select(ClassType)
            .options(selectinload(ClassType.subcategory).selectinload(ClassSubcategory.category))
            .where(ClassType.id == class_type_id)
        )
        return self.db.scalar(statement)

    def get_class_type_availability(
        self,
        class_type_id: int,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        trainer_id: int | None = None,
        query_type: str | None = None,
    ) -> list[Slot]:
        # Adapted from clinic GetAvailableServiceAppointments query semantics.
        statement = (
            select(Slot)
            .options(selectinload(Slot.trainer).selectinload(Trainer.disciplines))
            .join(Slot.class_type)
            .where(ClassType.id == class_type_id)
        )
        statement = statement.where(Slot.is_available.is_(True))
        if date_from is not None:
            statement = statement.where(Slot.slot_datetime >= date_from)
        if date_to is not None:
            statement = statement.where(Slot.slot_datetime <= date_to)
        if trainer_id is not None:
            statement = statement.where(Slot.trainer_id == trainer_id)
        if query_type == "2" and trainer_id is None:
            return []
        return list(self.db.scalars(statement.order_by(Slot.slot_datetime)).all())

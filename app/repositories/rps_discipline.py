from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Discipline,
    Location,
    MembershipPlan,
    Slot,
    Trainer,
)


# Adapted repository from clinic Specialty queries and specialty-based availability/professional filters.
class DisciplineRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_disciplines(self, search: str | None = None, page: int = 1, page_size: int = 20) -> tuple[list[Discipline], int]:
        statement = select(Discipline).options(selectinload(Discipline.trainers))
        count_statement = select(func.count()).select_from(Discipline)
        if search:
            pattern = f"%{search}%"
            condition = or_(Discipline.name.ilike(pattern), Discipline.description.ilike(pattern))
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)
        total = int(self.db.scalar(count_statement) or 0)
        items = self.db.scalars(statement.order_by(Discipline.name).offset((page - 1) * page_size).limit(page_size)).all()
        return list(items), total

    def get_discipline(self, discipline_id: int) -> Discipline | None:
        statement = select(Discipline).options(selectinload(Discipline.trainers)).where(Discipline.id == discipline_id)
        return self.db.scalar(statement)

    def get_trainers(self, discipline_id: int, membership_plan_id: int | None = None, location_code: str | None = None) -> list[Trainer]:
        statement = select(Trainer).join(Trainer.disciplines).where(Discipline.id == discipline_id)
        if membership_plan_id is not None:
            statement = statement.join(Trainer.membership_plans).where(MembershipPlan.id == membership_plan_id)
        if location_code is not None:
            statement = statement.join(Trainer.location).where(Location.location_code == location_code)
        return list(self.db.scalars(statement.order_by(Trainer.full_name)).all())

    def get_availability(
        self,
        discipline_id: int,
        date_from: datetime,
        date_to: datetime,
        trainer_id: int | None = None,
        is_online: bool | None = None,
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
        if is_online is not None:
            statement = statement.where(Slot.is_online == is_online)
        if location_code is not None:
            statement = statement.join(Slot.location).where(Location.location_code == location_code)
        return list(self.db.scalars(statement.order_by(Slot.slot_datetime)).all())

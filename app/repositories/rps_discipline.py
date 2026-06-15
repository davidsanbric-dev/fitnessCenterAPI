from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Discipline,
    Location,
    MembershipPlan,
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

    def get_by_id(self, discipline_id: int) -> Discipline | None:
        return self.db.scalar(select(Discipline).where(Discipline.id == discipline_id))

    def get_trainers(self, discipline_id: int, membership_plan_id: int | None = None, location_code: str | None = None) -> list[Trainer]:
        statement = select(Trainer).join(Trainer.disciplines).where(Discipline.id == discipline_id)
        if membership_plan_id is not None:
            statement = statement.join(Trainer.membership_plans).where(MembershipPlan.id == membership_plan_id)
        if location_code is not None:
            statement = statement.join(Trainer.location).where(Location.location_code == location_code)
        return list(self.db.scalars(statement.order_by(Trainer.full_name)).all())

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Discipline,
    Location,
    MembershipPlan,
    Slot,
    Trainer,
)


# Adapted repository from clinic GetProfessionalsByPrevision and professional availability queries.
class TrainerRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_trainers(
        self,
        discipline_id: int | None = None,
        membership_plan_id: int | None = None,
        location_code: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Trainer], int]:
        # Adapted professional listing filters: specialty/prevision/branch -> discipline/membership/location.
        statement = select(Trainer).options(selectinload(Trainer.disciplines), selectinload(Trainer.location)).where(Trainer.is_active.is_(True))
        count_statement = select(func.count()).select_from(Trainer).where(Trainer.is_active.is_(True))

        if discipline_id is not None:
            statement = statement.join(Trainer.disciplines).where(Discipline.id == discipline_id)
            count_statement = count_statement.join(Trainer.disciplines).where(Discipline.id == discipline_id)
        if membership_plan_id is not None:
            statement = statement.join(Trainer.membership_plans).where(MembershipPlan.id == membership_plan_id)
            count_statement = count_statement.join(Trainer.membership_plans).where(MembershipPlan.id == membership_plan_id)
        if location_code is not None:
            statement = statement.join(Trainer.location).where(Location.location_code == location_code)
            count_statement = count_statement.join(Trainer.location).where(Location.location_code == location_code)
        if search:
            pattern = f"%{search}%"
            statement = statement.where(or_(Trainer.full_name.ilike(pattern), Trainer.bio.ilike(pattern)))
            count_statement = count_statement.where(or_(Trainer.full_name.ilike(pattern), Trainer.bio.ilike(pattern)))

        total = int(self.db.scalar(count_statement) or 0)
        items = self.db.scalars(statement.order_by(Trainer.full_name).offset((page - 1) * page_size).limit(page_size)).all()
        return list(items), total

    def get_max_trainer_code(self, company_id: int) -> int | None:
        return self.db.scalar(select(func.max(Trainer.trainer_code)).where(Trainer.company_id == company_id))

    def get_by_user_id(self, user_id: int) -> Trainer | None:
        # Resolve the staff trainer linked to a signed-in user (see Trainer.user_id).
        statement = (
            select(Trainer)
            .options(selectinload(Trainer.disciplines), selectinload(Trainer.location))
            .where(Trainer.user_id == user_id)
        )
        return self.db.scalar(statement)

    def update_trainer(self, trainer: Trainer, fields: dict) -> Trainer:
        # Only the trainer's editable personal data; identity keys are untouched.
        for key in ("full_name", "bio", "photo_url", "certifications"):
            if key in fields and fields[key] is not None:
                setattr(trainer, key, fields[key])
        self.db.commit()
        self.db.refresh(trainer)
        return trainer

    def get_trainer(self, trainer_id: int) -> Trainer | None:
        statement = (
            select(Trainer)
            .options(selectinload(Trainer.disciplines), selectinload(Trainer.slots).selectinload(Slot.discipline))
            .where(Trainer.id == trainer_id)
        )
        return self.db.scalar(statement)

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories.rps_discipline import DisciplineRepository
from app.repositories.rps_slot import SlotRepository
from app.schemas import PaginatedResponse
from app.schemas.scm_discipline import (
    DisciplineAvailabilityResponse,
    DisciplineDetailResponse,
    DisciplineSummary,
    DisciplineTrainerSummary,
)
from app.services.svc_common import get_or_404


class DisciplineService:
    def __init__(self, db: Session):
        self.repository = DisciplineRepository(db)
        self.slots = SlotRepository(db)

    def list_disciplines(
        self,
        search: str | None,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[DisciplineSummary]:
        items, total = self.repository.list_disciplines(
            search=search, page=page, page_size=page_size
        )
        summaries = [DisciplineSummary.from_model(item) for item in items]
        return PaginatedResponse[DisciplineSummary].build(
            items=summaries,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_discipline(self, discipline_id: int) -> DisciplineDetailResponse:
        discipline = get_or_404(self.repository.get_discipline(discipline_id), "Discipline not found")
        return DisciplineDetailResponse.from_model(discipline)

    def get_trainers(self, discipline_id: int, membership_plan_id: int | None) -> dict:
        trainers = self.repository.get_trainers(discipline_id, membership_plan_id)
        return {
            "items": [DisciplineTrainerSummary.from_model(trainer) for trainer in trainers],
            "total": len(trainers),
        }

    def get_availability(
        self,
        discipline_id: int,
        date_from: datetime,
        date_to: datetime,
        trainer_id: int | None,
    ) -> DisciplineAvailabilityResponse:
        slots = self.slots.get_availability_by_discipline(discipline_id, date_from, date_to, trainer_id)
        return DisciplineAvailabilityResponse.from_slots(discipline_id, slots)

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories.rps_discipline import DisciplineRepository
from app.repositories.rps_location import LocationRepository
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
        self.locations = LocationRepository(db)
        self.slots = SlotRepository(db)

    def list_disciplines(
        self,
        search: str | None,
        page: int,
        page_size: int,
        location_code: str | None = None,
    ) -> PaginatedResponse[DisciplineSummary]:
        items, total = self.repository.list_disciplines(
            search=search, page=page, page_size=page_size, location_code=location_code
        )
        if location_code:
            # Scoped to a club: every row is offered there, so stamp its name once.
            location = self.locations.get_by_code(location_code)
            scoped_id = location.id if location else None
            scoped_name = location.name if location else None
            summaries = [
                DisciplineSummary.from_model(item, location_id=scoped_id, location_name=scoped_name)
                for item in items
            ]
        else:
            # Unscoped: each row carries its own offering club, derived from slots.
            summaries = []
            for item in items:
                offering_id, offering_name = self._resolve_offering_location(item)
                summaries.append(
                    DisciplineSummary.from_model(item, location_id=offering_id, location_name=offering_name)
                )
        return PaginatedResponse[DisciplineSummary].build(
            items=summaries,
            total=total,
            page=page,
            page_size=page_size,
        )

    @staticmethod
    def _resolve_offering_location(discipline) -> tuple[int | None, str | None]:
        # Distinct clubs the discipline has slots at. One club -> stamp it with
        # its id; several -> list the names (no single id); none -> leave blank.
        clubs: dict[int, str] = {}
        for slot in discipline.slots:
            location = slot.location
            if location is not None:
                clubs.setdefault(location.id, location.name)
        if not clubs:
            # No scheduled sessions yet: fall back to the clubs its trainers
            # work at so the directory still shows where it's offered.
            for trainer in discipline.trainers:
                location = trainer.location
                if location is not None:
                    clubs.setdefault(location.id, location.name)
        if not clubs:
            return None, None
        if len(clubs) == 1:
            (club_id, club_name), = clubs.items()
            return club_id, club_name
        return None, ", ".join(sorted(clubs.values()))

    def get_discipline(self, discipline_id: int) -> DisciplineDetailResponse:
        discipline = get_or_404(self.repository.get_discipline(discipline_id), "Discipline not found")
        return DisciplineDetailResponse.from_model(discipline)

    def get_trainers(self, discipline_id: int, membership_plan_id: int | None, location_code: str | None) -> dict:
        trainers = self.repository.get_trainers(discipline_id, membership_plan_id, location_code)
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
        location_code: str | None,
    ) -> DisciplineAvailabilityResponse:
        slots = self.slots.get_availability_by_discipline(discipline_id, date_from, date_to, trainer_id, location_code)
        return DisciplineAvailabilityResponse.from_slots(discipline_id, slots)

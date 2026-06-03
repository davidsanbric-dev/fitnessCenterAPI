from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.rps_discipline import DisciplineRepository


# Adapted service from clinic specialty discovery and availability flows.
class DisciplineService:
    def __init__(self, db: Session):
        self.repository = DisciplineRepository(db)

    def list_disciplines(self, search: str | None, page: int, page_size: int) -> dict:
        items, total = self.repository.list_disciplines(search=search, page=page, page_size=page_size)
        return {
            "items": [
                {
                    "discipline_id": item.id,
                    "discipline_code": item.discipline_code,
                    "name": item.name,
                    "description": item.description,
                    "icon_url": item.icon_url,
                    "trainers_count": len(item.trainers),
                }
                for item in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_discipline(self, discipline_id: int) -> dict:
        discipline = self.repository.get_discipline(discipline_id)
        if discipline is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discipline not found")
        return {
            "discipline_id": discipline.id,
            "discipline_code": discipline.discipline_code,
            "name": discipline.name,
            "description": discipline.description,
            "icon_url": discipline.icon_url,
            "trainers": [
                {
                    "trainer_id": trainer.id,
                    "full_name": trainer.full_name,
                    "bio": trainer.bio,
                    "photo_url": trainer.photo_url,
                }
                for trainer in discipline.trainers
            ],
        }

    def get_trainers(self, discipline_id: int, membership_plan_id: int | None, location_code: str | None) -> dict:
        discipline = self.repository.get_discipline(discipline_id)
        if discipline is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discipline not found")
        trainers = self.repository.get_trainers(discipline_id, membership_plan_id, location_code)
        return {
            "items": [
                {
                    "trainer_id": trainer.id,
                    "full_name": trainer.full_name,
                    "bio": trainer.bio,
                    "photo_url": trainer.photo_url,
                }
                for trainer in trainers
            ],
            "total": len(trainers),
        }

    def get_availability(
        self,
        discipline_id: int,
        date_from: datetime,
        date_to: datetime,
        trainer_id: int | None,
        location_code: str | None,
    ) -> dict:
        discipline = self.repository.get_discipline(discipline_id)
        if discipline is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discipline not found")
        slots = self.repository.get_availability(discipline_id, date_from, date_to, trainer_id, location_code)
        return {
            "discipline_id": discipline_id,
            "slots": [
                {
                    "slot_datetime": slot.slot_datetime,
                    "location_id": slot.location_id,
                    "trainer": {
                        "trainer_id": slot.trainer.id,
                        "full_name": slot.trainer.full_name,
                        "discipline_id": slot.discipline.id if slot.discipline else None,
                        "discipline_name": slot.discipline.name if slot.discipline else None,
                    },
                }
                for slot in slots
                if slot.trainer is not None
            ],
        }

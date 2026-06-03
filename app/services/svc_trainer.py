from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.rps_trainer import TrainerRepository
from app.services.svc_common import serialize_trainer_summary


# Adapted service from clinic professional directory and availability flows.
class TrainerService:
    def __init__(self, db: Session):
        self.repository = TrainerRepository(db)

    def list_trainers(self, **filters) -> dict:
        items, total = self.repository.list_trainers(**filters)
        return {
            "items": [serialize_trainer_summary(item) for item in items],
            "total": total,
            "page": filters["page"],
            "page_size": filters["page_size"],
        }

    def get_trainer(self, trainer_id: int) -> dict:
        trainer = self.repository.get_trainer(trainer_id)
        if trainer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trainer not found")
        upcoming = [
            {
                "slot_datetime": slot.slot_datetime,
                "location_id": slot.location_id,
                "is_available": slot.is_available,
                "discipline_name": slot.discipline.name if slot.discipline else None,
            }
            for slot in trainer.slots
            if slot.slot_datetime >= datetime.utcnow() and slot.slot_datetime <= datetime.utcnow() + timedelta(days=14)
        ]
        return {
            "trainer_id": trainer.id,
            "trainer_code": trainer.trainer_code,
            "full_name": trainer.full_name,
            "bio": trainer.bio,
            "photo_url": trainer.photo_url,
            "certifications": trainer.certifications or [],
            "disciplines": [
                {
                    "discipline_id": discipline.id,
                    "discipline_code": discipline.discipline_code,
                    "discipline_name": discipline.name,
                }
                for discipline in trainer.disciplines
            ],
            "upcoming_availability": upcoming,
        }

    def get_availability(self, trainer_id: int, date_from: datetime, date_to: datetime, discipline_id: int | None = None) -> dict:
        trainer = self.repository.get_trainer(trainer_id)
        if trainer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trainer not found")
        slots = self.repository.get_availability(trainer_id, date_from, date_to, discipline_id)
        return {
            "trainer_id": trainer_id,
            "slots": [
                {
                    "slot_datetime": slot.slot_datetime,
                    "location_id": slot.location_id,
                    "is_available": slot.is_available,
                    "discipline_name": slot.discipline.name if slot.discipline else None,
                }
                for slot in slots
            ],
        }

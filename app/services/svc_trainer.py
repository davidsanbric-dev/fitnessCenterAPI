from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.push import send_push_to_tokens
from app.models import Slot, Trainer, User
from app.repositories.rps_notification import NotificationRepository
from app.repositories.rps_slot import SlotRepository
from app.repositories.rps_trainer import TrainerRepository
from app.services.svc_common import serialize_trainer_summary

logger = logging.getLogger("uvicorn.error")


# Adapted service from clinic professional directory and availability flows.
class TrainerService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = TrainerRepository(db)
        self.slots = SlotRepository(db)
        self.notifications = NotificationRepository(db)

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

    # ---- trainer self-service ("me") ----------------------------------------
    # All of the below resolve the Trainer record from the signed-in user, so a
    # trainer can only ever read/mutate its own personal data and slots.

    def _require_self(self, user: User) -> Trainer:
        trainer = self.repository.get_by_user_id(user.id)
        if trainer is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No trainer profile is linked to this account",
            )
        return trainer

    def _serialize_profile(self, trainer: Trainer, email: str) -> dict:
        return {
            "trainer_id": trainer.id,
            "trainer_code": trainer.trainer_code,
            "full_name": trainer.full_name,
            "email": email,
            "bio": trainer.bio,
            "photo_url": trainer.photo_url,
            "certifications": trainer.certifications or [],
            "location_id": trainer.location_id,
            "disciplines": [
                {
                    "discipline_id": discipline.id,
                    "discipline_code": discipline.discipline_code,
                    "discipline_name": discipline.name,
                }
                for discipline in trainer.disciplines
            ],
        }

    @staticmethod
    def _serialize_slot(slot: Slot) -> dict:
        return {
            "slot_id": slot.id,
            "slot_datetime": slot.slot_datetime,
            "location_id": slot.location_id,
            "discipline_id": slot.discipline_id,
            "discipline_name": slot.discipline.name if slot.discipline else None,
            "is_available": slot.is_available,
            "slot_assignment_code": slot.slot_assignment_code,
            "schedule_type": slot.schedule_type,
        }

    def get_my_profile(self, user: User) -> dict:
        return self._serialize_profile(self._require_self(user), user.email)

    def update_my_profile(self, user: User, payload: dict) -> dict:
        trainer = self._require_self(user)
        trainer = self.repository.update_trainer(trainer, payload)
        return self._serialize_profile(trainer, user.email)

    def get_my_dashboard(self, user: User) -> dict:
        trainer = self._require_self(user)
        slots = self.slots.list_for_trainer(trainer.id)
        now = datetime.utcnow()
        upcoming = [slot for slot in slots if slot.slot_datetime >= now]
        return {
            "trainer": {
                "trainer_id": trainer.id,
                "full_name": trainer.full_name,
                "trainer_code": trainer.trainer_code,
            },
            "kpis": {
                "total_slots": len(slots),
                "available_slots": sum(1 for slot in slots if slot.is_available),
                "upcoming_slots": len(upcoming),
                "booked_slots": sum(1 for slot in slots if not slot.is_available),
            },
            "upcoming_slots": [self._serialize_slot(slot) for slot in upcoming[:5]],
        }

    def list_my_slots(self, user: User) -> list[dict]:
        trainer = self._require_self(user)
        return [self._serialize_slot(slot) for slot in self.slots.list_for_trainer(trainer.id)]

    def create_my_slot(self, user: User, payload: dict) -> dict:
        trainer = self._require_self(user)
        slot = Slot(
            slot_datetime=payload["slot_datetime"],
            location_id=trainer.location_id,
            trainer_id=trainer.id,
            discipline_id=payload.get("discipline_id"),
            is_available=True,
            schedule_type=payload.get("schedule_type") or "PERSONAL",
        )
        slot = self.slots.create_slot(slot)
        self._notify_members_of_slot_change("created", trainer, slot)
        return self._serialize_slot(self.slots.get_slot(slot.id) or slot)

    def update_my_slot(self, user: User, slot_id: int, payload: dict) -> dict:
        trainer = self._require_self(user)
        slot = self._require_own_slot(trainer, slot_id)
        slot = self.slots.update_slot(slot, payload)
        self._notify_members_of_slot_change("updated", trainer, slot)
        return self._serialize_slot(slot)

    def delete_my_slot(self, user: User, slot_id: int) -> None:
        trainer = self._require_self(user)
        slot = self._require_own_slot(trainer, slot_id)
        # Snapshot before deletion so the push can reference the freed time.
        self._notify_members_of_slot_change("removed", trainer, slot)
        self.slots.delete_slot(slot)

    def _require_own_slot(self, trainer: Trainer, slot_id: int) -> Slot:
        slot = self.slots.get_slot(slot_id)
        if slot is None or slot.trainer_id != trainer.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")
        return slot

    def _notify_members_of_slot_change(self, action: str, trainer: Trainer, slot: Slot) -> None:
        # Best-effort FCM broadcast to every device registered for this company
        # (device tokens are tenant-scoped, and only members register them from
        # the mobile app). A push failure must never break the slot mutation.
        # Mirrors the blog-created push (see app.services.svc_blog).
        try:
            when = slot.slot_datetime.strftime("%b %d, %H:%M")
            bodies = {
                "created": f"{trainer.full_name} opened a new slot on {when}.",
                "updated": f"{trainer.full_name} updated a slot ({when}).",
                "removed": f"{trainer.full_name} removed a slot ({when}).",
            }
            tokens = [device.token for device in self.notifications.list_device_tokens()]
            if not tokens:
                return
            invalid = send_push_to_tokens(
                tokens,
                title="Trainer availability updated",
                body=bodies.get(action, "A trainer slot changed."),
                data={
                    "type": "slot_updated",
                    "action": action,
                    "slot_id": slot.id,
                    "trainer_id": trainer.id,
                },
            )
            if invalid:
                self.notifications.prune_tokens(invalid)
        except Exception:
            logger.warning("Failed to dispatch slot push notification", exc_info=True)

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    InternalServerErrorException,
    NotFoundException,
)
from app.core.firebase_auth import create_or_align_firebase_account
from app.core.push import send_push_to_tokens
from app.core.tenancy import get_session_company
from app.models import Discipline, Location, Role, Slot, Trainer, User
from app.repositories.rps_notification import NotificationRepository
from app.repositories.rps_slot import SlotRepository
from app.repositories.rps_trainer import TrainerRepository
from app.services.svc_common import get_or_404, serialize_trainer_summary

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
        trainer = get_or_404(self.repository.get_trainer(trainer_id), "Trainer not found")
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
        trainer = get_or_404(self.repository.get_trainer(trainer_id), "Trainer not found")
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

    # ---- admin staff-trainer provisioning -----------------------------------
    # Base trainer_code for admin-created staff trainers, kept clear of the seeded
    # catalog (1001/1002) and demo-staff (2001) codes. The next free code within
    # the company is allocated upward from here.
    _ADMIN_TRAINER_CODE_BASE = 3000

    def admin_create_trainer(self, payload: dict) -> dict:
        # Provision a new staff trainer from the admin web: a Firebase credential,
        # a User bound to the "trainer" role, and the linked Trainer record holding
        # its personal data. Mirrors the seed's staff-trainer provisioning but at
        # runtime, scoped to the calling admin's company (tenant set on the session).
        email = str(payload["email"]).strip().lower()
        full_name = str(payload["full_name"]).strip()
        password = str(payload["password"])

        # Roles are the global authorization catalogue (not tenant scoped); its
        # absence means the deployment was never seeded.
        role = self.db.scalar(select(Role).where(Role.name == "trainer"))
        if role is None:
            raise InternalServerErrorException("Trainer role is not provisioned")

        company_id = get_session_company(self.db)

        # Next free trainer_code within the company (codes are unique per company).
        max_code = self.db.scalar(select(func.max(Trainer.trainer_code)).where(Trainer.company_id == company_id))
        trainer_code = max(int(max_code or 0), self._ADMIN_TRAINER_CODE_BASE) + 1

        # Anchor the trainer at the company's first location, mirroring the seed.
        location = self.db.scalar(select(Location).order_by(Location.id))

        # Optional discipline: only attach one that belongs to this company (the
        # session is tenant-scoped) so the trainer's future slots are meaningful.
        discipline = None
        discipline_id = payload.get("discipline_id")
        if discipline_id:
            discipline = self.db.scalar(select(Discipline).where(Discipline.id == discipline_id))
            if discipline is None:
                raise NotFoundException("Discipline not found")

        # Provision the backend rows first so the globally-unique email constraint
        # is the authoritative duplicate guard — it also catches cross-company
        # duplicates the tenant-scoped session cannot see. company_id is auto-
        # stamped on flush by the tenancy event.
        user = User(email=email, role_id=role.id, is_active=True)
        self.db.add(user)
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictException("Email already registered") from exc

        trainer = Trainer(
            trainer_code=trainer_code,
            full_name=full_name,
            bio=payload.get("bio"),
            photo_url=payload.get("photo_url") or "/images/trainers/staff.jpg",
            certifications=payload.get("certifications") or [],
            is_active=True,
            location_id=location.id if location else None,
            user_id=user.id,
        )
        if discipline is not None:
            trainer.disciplines.append(discipline)
        self.db.add(trainer)

        # Create the credential only now that the email is known free, so a
        # conflict above never leaves an orphan Firebase account. Done before the
        # commit so a Firebase failure rolls back the half-provisioned rows.
        create_or_align_firebase_account(email, password)

        self.db.commit()
        self.db.refresh(trainer)
        return self._serialize_profile(trainer, email)

    # ---- trainer self-service ("me") ----------------------------------------
    # All of the below resolve the Trainer record from the signed-in user, so a
    # trainer can only ever read/mutate its own personal data and slots.

    def _require_self(self, user: User) -> Trainer:
        trainer = self.repository.get_by_user_id(user.id)
        if trainer is None:
            raise ForbiddenException("No trainer profile is linked to this account")
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
            raise NotFoundException("Slot not found")
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

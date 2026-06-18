from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ForbiddenException,
    InternalServerErrorException,
)
from app.core.firebase_auth import create_or_align_firebase_account
from app.core.media import delete_profile_image, save_profile_image
from app.core.tenancy import get_session_company
from app.models import Slot, Trainer, User
from app.repositories.rps_discipline import DisciplineRepository
from app.repositories.rps_role import RoleRepository
from app.repositories.rps_trainer import TrainerRepository
from app.schemas import PaginatedResponse
from app.schemas.scm_trainer import (
    TrainerAvailabilityResponse,
    TrainerDashboardResponse,
    TrainerDetailResponse,
    TrainerMeProfileResponse,
    TrainerSlotResponse,
    TrainerSummary,
)
from app.services.svc_common import get_or_404
from app.services.svc_notification import NotificationService
from app.services.svc_slot import SlotService
from app.services.svc_user import UserService


class TrainerService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = TrainerRepository(db)
        self.disciplines = DisciplineRepository(db)
        self.roles = RoleRepository(db)
        self.slot_service = SlotService(db)
        self.notifications = NotificationService(db)
        self.users = UserService(db)

    def list_trainers(self, **filters) -> PaginatedResponse[TrainerSummary]:
        items, total = self.repository.list_trainers(**filters)
        return PaginatedResponse[TrainerSummary].build(
            items=[TrainerSummary.from_model(item) for item in items],
            total=total,
            page=filters["page"],
            page_size=filters["page_size"],
        )

    def get_trainer(self, trainer_id: int) -> TrainerDetailResponse:
        trainer = get_or_404(self.repository.get_trainer(trainer_id), "Trainer not found")
        return TrainerDetailResponse.from_model(trainer)

    def get_availability(self, trainer_id: int, date_from: datetime, date_to: datetime, discipline_id: int | None = None) -> TrainerAvailabilityResponse:
        slots = self.slot_service.get_availability_by_trainer(trainer_id, date_from, date_to, discipline_id)
        return TrainerAvailabilityResponse.from_slots(trainer_id, slots)

    _ADMIN_TRAINER_CODE_BASE = 3000

    def admin_create_trainer(self, payload: dict) -> dict:
        email = str(payload["email"]).strip().lower()
        full_name = str(payload["full_name"]).strip()
        password = str(payload["password"])

        role = self.roles.get_by_name("trainer")
        if role is None:
            raise InternalServerErrorException("Trainer role is not provisioned")

        company_id = get_session_company(self.db)

        max_code = self.repository.get_max_trainer_code(company_id)
        trainer_code = max(int(max_code or 0), self._ADMIN_TRAINER_CODE_BASE) + 1

        discipline = None
        discipline_id = payload.get("discipline_id")
        if discipline_id:
            discipline = get_or_404(self.disciplines.get_by_id(discipline_id), "Discipline not found")

        user = self.users.create_user(email, role.id)

        trainer = Trainer(
            trainer_code=trainer_code,
            full_name=full_name,
            bio=payload.get("bio"),
            photo_url=payload.get("photo_url") or "/images/trainers/staff.jpg",
            certifications=payload.get("certifications") or [],
            is_active=True,
            user_id=user.id,
        )
        if discipline is not None:
            trainer.disciplines.append(discipline)
        self.db.add(trainer)

        create_or_align_firebase_account(email, password)

        self.db.commit()
        self.db.refresh(trainer)
        return TrainerMeProfileResponse.from_trainer(trainer, email)

    def _require_self(self, user: User) -> Trainer:
        trainer = self.repository.get_by_user_id(user.id)
        if trainer is None:
            raise ForbiddenException("No trainer profile is linked to this account")
        return trainer

    def get_my_profile(self, user: User) -> TrainerMeProfileResponse:
        return TrainerMeProfileResponse.from_trainer(self._require_self(user), user.email)

    def update_my_profile(self, user: User, payload: dict) -> TrainerMeProfileResponse:
        trainer = self._require_self(user)
        # A new photo is uploaded as base64; persist it to the profile-image
        # volume and derive ``photo_url`` from the stored filename, reclaiming the
        # previous owned file. Mirrors BlogService image handling.
        raw_image = payload.pop("photo_image", None)
        if raw_image:
            old_photo = trainer.photo_url
            payload["photo_url"] = save_profile_image(self.db, raw_image)
            if old_photo and old_photo != payload["photo_url"]:
                delete_profile_image(old_photo)
        trainer = self.repository.update_trainer(trainer, payload)
        return TrainerMeProfileResponse.from_trainer(trainer, user.email)

    def get_my_dashboard(self, user: User) -> TrainerDashboardResponse:
        trainer = self._require_self(user)
        slots = self.slot_service.list_for_trainer(trainer.id)
        return TrainerDashboardResponse.build(trainer, slots)

    def list_my_slots(self, user: User) -> list[TrainerSlotResponse]:
        trainer = self._require_self(user)
        return [TrainerSlotResponse.from_model(slot) for slot in self.slot_service.list_for_trainer(trainer.id)]

    def create_my_slot(self, user: User, payload: dict) -> TrainerSlotResponse:
        trainer = self._require_self(user)
        slot = self.slot_service.create_slot(trainer, payload)
        self._notify_members_of_slot_change("created", trainer, slot)
        return TrainerSlotResponse.from_model(self.slot_service.get_slot(slot.id) or slot)

    def update_my_slot(self, user: User, slot_id: int, payload: dict) -> TrainerSlotResponse:
        trainer = self._require_self(user)
        slot = self.slot_service.require_own_slot(trainer.id, slot_id)
        slot = self.slot_service.update_slot(slot, payload)
        self._notify_members_of_slot_change("updated", trainer, slot)
        return TrainerSlotResponse.from_model(slot)

    def delete_my_slot(self, user: User, slot_id: int) -> None:
        trainer = self._require_self(user)
        slot = self.slot_service.require_own_slot(trainer.id, slot_id)
        self._notify_members_of_slot_change("removed", trainer, slot)
        self.slot_service.delete_slot(slot)

    def _notify_members_of_slot_change(self, action: str, trainer: Trainer, slot: Slot) -> None:
        when = slot.slot_datetime.strftime("%b %d, %H:%M")
        bodies = {
            "created": f"{trainer.full_name} opened a new slot on {when}.",
            "updated": f"{trainer.full_name} updated a slot ({when}).",
            "removed": f"{trainer.full_name} removed a slot ({when}).",
        }
        self.notifications.broadcast_push(
            title="Trainer availability updated",
            body=bodies.get(action, "A trainer slot changed."),
            data={
                "type": "slot_updated",
                "action": action,
                "slot_id": slot.id,
                "trainer_id": trainer.id,
            },
        )

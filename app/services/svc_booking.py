from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Booking, User
from app.repositories.rps_booking import BookingRepository
from app.repositories.rps_user import UserRepository
from app.services.svc_common import parse_datetime_parts, serialize_booking
from app.services.svc_notification import NotificationService


# Adapted service from clinic appointment scheduling/agenda/status-update use cases.
class BookingService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = BookingRepository(db)
        self.user_repository = UserRepository(db)
        self.notifications = NotificationService(db)

    def _member_label(self, booking: Booking) -> str:
        profile = booking.user.profile if booking.user else None
        if profile is not None:
            label = f"{profile.first_name} {profile.paternal_surname}".strip()
            if label:
                return label
        return booking.user.email if booking.user else "A member"

    def _session_label(self, booking: Booking) -> str:
        if booking.class_type is not None:
            return booking.class_type.name
        if booking.discipline is not None:
            return booking.discipline.name
        return "a session"

    def _notify_staff_of_booking_event(
        self, booking: Booking, title: str, body: str, notification_type: str, acting_user_id: int
    ) -> None:
        # Fan a member-driven booking action out to the web-app staff: the slot's
        # linked trainer (when the trainer has a login) plus all admins/managers
        # in the company. The acting member is excluded so they don't self-notify.
        recipients = self.user_repository.list_staff_user_ids(("admin", "manager"))
        if booking.trainer is not None and booking.trainer.user_id is not None:
            recipients.append(booking.trainer.user_id)
        recipients = [uid for uid in recipients if uid != acting_user_id]
        if not recipients:
            return
        self.notifications.notify_many(
            recipients,
            title,
            body,
            notification_type,
            {"booking_id": booking.id, "member_id": booking.user_id},
        )

    def create_by_trainer(self, user: User, payload) -> dict:
        # Adapted Path A from ScheduleAppointmentCommand.
        booking_datetime = parse_datetime_parts(payload.booking_date, payload.booking_time)
        if self.repository.user_has_booking_at(user.id, booking_datetime):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have a booking at that time")
        slot = self.repository.get_slot_for_trainer_booking(
            booking_datetime,
            payload.location_code,
            payload.trainer_code,
            payload.discipline_code,
        )
        if slot is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Selected slot is not available")
        booking = Booking(
            user_id=user.id,
            slot_id=slot.id,
            booking_status="CONFIRMED",
            booking_datetime=booking_datetime,
            session_duration_minutes=payload.session_duration_minutes,
            preparation_info=slot.class_type.preparation_info if slot.class_type else None,
            has_pdf=bool(slot.class_type and slot.class_type.pdf_code),
            pdf_code=slot.class_type.pdf_code if slot.class_type else None,
            notes=payload.notes,
            trainer_id=slot.trainer_id,
            discipline_id=slot.discipline_id,
            class_type_id=slot.class_type_id,
            category_id=slot.class_type.subcategory.category_id if slot.class_type else None,
            location_id=slot.location_id,
            slot_assignment_code=slot.slot_assignment_code,
        )
        booking = self.repository.create_booking(booking, slot)
        if user.membership is not None:
            user.membership.bookings_used += 1
            self.db.commit()
        self.notifications.notify(user.id, "Booking confirmed", "Your trainer session has been booked.", "booking_confirmed", {"booking_id": booking.id})
        self._notify_staff_of_booking_event(
            booking,
            "New booking",
            f"{self._member_label(booking)} booked {self._session_label(booking)} for {booking.booking_datetime:%d %b %H:%M}.",
            "booking_created",
            user.id,
        )
        return serialize_booking(booking)

    def create_by_class_type(self, user: User, payload) -> dict:
        # Adapted Path B from ScheduleServiceAppointmentCommand.
        booking_datetime = parse_datetime_parts(payload.booking_date, payload.booking_time)
        if self.repository.user_has_booking_at(user.id, booking_datetime):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have a booking at that time")
        slot = self.repository.get_slot_for_class_type_booking(
            booking_datetime,
            payload.location_code,
            payload.trainer_code,
            payload.class_type_id,
            payload.slot_assignment_code,
        )
        if slot is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Selected slot is not available")
        booking = Booking(
            user_id=user.id,
            slot_id=slot.id,
            booking_status="CONFIRMED",
            booking_datetime=booking_datetime,
            session_duration_minutes=60,
            preparation_info=slot.class_type.preparation_info if slot.class_type else None,
            has_pdf=bool(slot.class_type and slot.class_type.pdf_code),
            pdf_code=slot.class_type.pdf_code if slot.class_type else None,
            notes=payload.notes,
            trainer_id=slot.trainer_id,
            discipline_id=slot.discipline_id,
            class_type_id=slot.class_type_id,
            category_id=slot.class_type.subcategory.category_id if slot.class_type else None,
            location_id=slot.location_id,
            slot_assignment_code=payload.slot_assignment_code,
        )
        booking = self.repository.create_booking(booking, slot)
        if user.membership is not None:
            user.membership.bookings_used += 1
            self.db.commit()
        self.notifications.notify(user.id, "Class booked", "Your class slot has been booked.", "booking_confirmed", {"booking_id": booking.id})
        self._notify_staff_of_booking_event(
            booking,
            "New booking",
            f"{self._member_label(booking)} booked {self._session_label(booking)} for {booking.booking_datetime:%d %b %H:%M}.",
            "booking_created",
            user.id,
        )
        return serialize_booking(booking)

    def list_bookings(self, user_id: int, **filters) -> dict:
        booking_status = filters.get("booking_status")
        if booking_status is not None and str(booking_status).strip() in {"", "0", "ALL", "all"}:
            filters["booking_status"] = None
        items, total = self.repository.list_bookings(user_id=user_id, **filters)
        return {
            "items": [serialize_booking(item) for item in items],
            "total": total,
            "page": filters["page"],
            "page_size": filters["page_size"],
        }

    def get_booking(self, user_id: int, booking_id: int, location_code: str) -> dict:
        booking = self.repository.get_booking(booking_id)
        if booking is None or booking.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
        if booking.location and booking.location.location_code != location_code:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found for location")
        return serialize_booking(booking)

    @staticmethod
    def _require_notes_for_completion(booking_status: str, notes: str | None) -> None:
        # Completing a session must carry a feedback note (surfaced to the member
        # in their Training History). Enforced server-side so the rule holds for
        # every caller -- trainer panel, admin panel, or member app.
        if booking_status == "COMPLETED" and not (notes or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A feedback note is required when marking a session as completed",
            )

    def update_status(self, user_id: int, booking_id: int, booking_status: str, location_code: str, notes: str | None) -> dict:
        # Adapted from UpdateAppointmentStatusCommand with gym cancellation policy extension.
        self._require_notes_for_completion(booking_status, notes)
        booking = self.repository.get_booking(booking_id)
        if booking is None or booking.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
        if booking.location and booking.location.location_code != location_code:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found for location")
        if booking_status == "CANCELLED" and booking.booking_datetime - datetime.utcnow() < timedelta(hours=2):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancellation window has passed")
        booking = self.repository.update_status(booking, booking_status, notes)
        self.notifications.notify(user_id, "Booking updated", f"Your booking is now {booking_status.lower()}.", "schedule_change", {"booking_id": booking.id})
        staff_title = "Booking cancelled" if booking_status == "CANCELLED" else "Booking updated"
        self._notify_staff_of_booking_event(
            booking,
            staff_title,
            f"{self._member_label(booking)} {booking_status.lower()} their {self._session_label(booking)} booking for {booking.booking_datetime:%d %b %H:%M}.",
            "schedule_change",
            user_id,
        )
        return {"booking_id": booking.id, "booking_status": booking.booking_status, "updated_at": booking.updated_at}

    def upcoming(self, user_id: int, limit: int) -> dict:
        items = self.repository.list_upcoming(user_id, limit)
        return {
            "items": [
                {
                    "booking_id": item.id,
                    "booking_datetime": item.booking_datetime,
                    "class_type": {
                        "class_type_id": item.class_type.id,
                        "name": item.class_type.name,
                        "type_name": item.class_type.schedule_type,
                    } if item.class_type else None,
                    "trainer": {
                        "trainer_id": item.trainer.id,
                        "full_name": item.trainer.full_name,
                        "discipline_id": item.discipline.id if item.discipline else None,
                        "discipline_name": item.discipline.name if item.discipline else None,
                    } if item.trainer else None,
                    "booking_status": item.booking_status,
                }
                for item in items
            ]
        }

    def list_all_bookings(self, **filters) -> dict:
        booking_status = filters.get("booking_status")
        if booking_status is not None and str(booking_status).strip() in {"", "0", "ALL", "all"}:
            filters["booking_status"] = None
        items, total = self.repository.list_all_bookings(**filters)
        return {
            "items": [serialize_booking(item) for item in items],
            "total": total,
            "page": filters["page"],
            "page_size": filters["page_size"],
        }

    def admin_update_status(self, booking_id: int, booking_status: str, location_code: str, notes: str | None) -> dict:
        self._require_notes_for_completion(booking_status, notes)
        booking = self.repository.get_booking(booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
        if booking.location and booking.location.location_code != location_code:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found for location")
        booking = self.repository.update_status(booking, booking_status, notes)
        self.notifications.notify(
            booking.user_id,
            "Booking updated",
            f"Your booking is now {booking_status.lower()}.",
            "schedule_change",
            {"booking_id": booking.id},
        )
        return {"booking_id": booking.id, "booking_status": booking.booking_status, "updated_at": booking.updated_at}

    def trainer_update_status(self, trainer_id: int, booking_id: int, booking_status: str, location_code: str, notes: str | None) -> dict:
        # Trainer self-service: a trainer may only update the status of bookings
        # assigned to their own trainer id. Mirrors admin_update_status but scoped
        # by ownership rather than admin/manager authorization.
        self._require_notes_for_completion(booking_status, notes)
        booking = self.repository.get_booking(booking_id)
        if booking is None or booking.trainer_id != trainer_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
        if booking.location and booking.location.location_code != location_code:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found for location")
        booking = self.repository.update_status(booking, booking_status, notes)
        self.notifications.notify(
            booking.user_id,
            "Booking updated",
            f"Your booking is now {booking_status.lower()}.",
            "schedule_change",
            {"booking_id": booking.id},
        )
        return {"booking_id": booking.id, "booking_status": booking.booking_status, "updated_at": booking.updated_at}

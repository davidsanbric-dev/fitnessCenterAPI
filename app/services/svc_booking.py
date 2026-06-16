from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.domain import (
    BookingStatus,
    enforce_cancellation_window,
    require_notes_for_completion,
)
from app.models import Booking, Slot, User
from app.repositories.rps_booking import BookingRepository
from app.repositories.rps_user import UserRepository
from app.schemas import PaginatedResponse
from app.schemas.scm_booking import (
    BookingByClassTypeCreate,
    BookingByTrainerCreate,
    BookingResponse,
    BookingStatusResponse,
    UpcomingBookingResponse,
)
from app.services.svc_common import parse_datetime_parts
from app.services.svc_notification import NotificationService
from app.services.validators import BookingGuards


class BookingService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = BookingRepository(db)
        self.user_repository = UserRepository(db)
        self.notifications = NotificationService(db)
        self.guards = BookingGuards(self.repository)

    @staticmethod
    def _build_booking(
        user: User,
        slot: Slot,
        booking_datetime: datetime,
        *,
        session_duration_minutes: int,
        slot_assignment_code: str | None,
        notes: str | None,
    ) -> Booking:
        class_type = slot.class_type
        return Booking(
            user_id=user.id,
            slot_id=slot.id,
            booking_status=BookingStatus.PENDING,
            booking_datetime=booking_datetime,
            session_duration_minutes=session_duration_minutes,
            preparation_info=class_type.preparation_info if class_type else None,
            has_pdf=bool(class_type and class_type.pdf_code),
            pdf_code=class_type.pdf_code if class_type else None,
            notes=notes,
            trainer_id=slot.trainer_id,
            discipline_id=slot.discipline_id,
            class_type_id=slot.class_type_id,
            category_id=class_type.subcategory.category_id if class_type else None,
            location_id=slot.location_id,
            slot_assignment_code=slot_assignment_code,
        )

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

    def create_by_trainer(self, user: User, payload: BookingByTrainerCreate) -> BookingResponse:
        self.guards.require_booking_allowance(user)
        booking_datetime = parse_datetime_parts(payload.booking_date, payload.booking_time)
        self.guards.require_no_existing_booking_at(user.id, booking_datetime)
        slot = self.guards.require_available_slot(
            self.repository.get_slot_for_trainer_booking(
                booking_datetime,
                payload.location_code,
                payload.trainer_code,
                payload.discipline_code,
            )
        )
        booking = self._build_booking(
            user,
            slot,
            booking_datetime,
            session_duration_minutes=payload.session_duration_minutes,
            slot_assignment_code=slot.slot_assignment_code,
            notes=payload.notes,
        )
        booking = self.repository.create_booking(booking, slot)
        if user.membership is not None:
            user.membership.bookings_used += 1
            self.db.commit()
        self.notifications.notify(user.id, "Booking requested", "Your trainer session is pending confirmation.", "booking_confirmed", {"booking_id": booking.id})
        self._notify_staff_of_booking_event(
            booking,
            "New booking",
            f"{self._member_label(booking)} booked {self._session_label(booking)} for {booking.booking_datetime:%d %b %H:%M}.",
            "booking_created",
            user.id,
        )
        return BookingResponse.from_model(booking)

    def create_by_class_type(self, user: User, payload: BookingByClassTypeCreate) -> BookingResponse:
        self.guards.require_booking_allowance(user)
        booking_datetime = parse_datetime_parts(payload.booking_date, payload.booking_time)
        self.guards.require_no_existing_booking_at(user.id, booking_datetime)
        slot = self.guards.require_available_slot(
            self.repository.get_slot_for_class_type_booking(
                booking_datetime,
                payload.location_code,
                payload.trainer_code,
                payload.class_type_id,
                payload.slot_assignment_code,
            )
        )
        booking = self._build_booking(
            user,
            slot,
            booking_datetime,
            session_duration_minutes=60,
            slot_assignment_code=payload.slot_assignment_code,
            notes=payload.notes,
        )
        booking = self.repository.create_booking(booking, slot)
        if user.membership is not None:
            user.membership.bookings_used += 1
            self.db.commit()
        self.notifications.notify(user.id, "Class requested", "Your class slot is pending confirmation.", "booking_confirmed", {"booking_id": booking.id})
        self._notify_staff_of_booking_event(
            booking,
            "New booking",
            f"{self._member_label(booking)} booked {self._session_label(booking)} for {booking.booking_datetime:%d %b %H:%M}.",
            "booking_created",
            user.id,
        )
        return BookingResponse.from_model(booking)

    def list_bookings(self, user_id: int, **filters) -> PaginatedResponse[BookingResponse]:
        booking_status = filters.get("booking_status")
        if booking_status is not None and str(booking_status).strip() in {"", "0", "ALL", "all"}:
            filters["booking_status"] = None
        items, total = self.repository.list_bookings(user_id=user_id, **filters)
        return PaginatedResponse[BookingResponse].build(
            items=[BookingResponse.from_model(item) for item in items],
            total=total,
            page=filters["page"],
            page_size=filters["page_size"],
        )

    def get_booking(self, user_id: int, booking_id: int, location_code: str) -> BookingResponse:
        booking = self.guards.require_existing_for_location(booking_id, location_code, user_id=user_id)
        return BookingResponse.from_model(booking)

    def update_status(self, user_id: int, booking_id: int, booking_status: str, location_code: str, notes: str | None) -> BookingStatusResponse:
        require_notes_for_completion(booking_status, notes)
        booking = self.guards.require_existing_for_location(booking_id, location_code, user_id=user_id)
        enforce_cancellation_window(booking_status, booking.booking_datetime)
        booking = self.repository.update_status(booking, booking_status, notes)
        self.notifications.notify(user_id, "Booking updated", f"Your booking is now {booking_status.lower()}.", "schedule_change", {"booking_id": booking.id})
        staff_title = "Booking cancelled" if booking_status == BookingStatus.CANCELLED else "Booking updated"
        self._notify_staff_of_booking_event(
            booking,
            staff_title,
            f"{self._member_label(booking)} {booking_status.lower()} their {self._session_label(booking)} booking for {booking.booking_datetime:%d %b %H:%M}.",
            "schedule_change",
            user_id,
        )
        return BookingStatusResponse.from_model(booking)

    def upcoming(self, user_id: int, limit: int) -> dict:
        items = self.repository.list_upcoming(user_id, limit)
        return {"items": [UpcomingBookingResponse.from_model(item) for item in items]}

    def list_all_bookings(self, **filters) -> PaginatedResponse[BookingResponse]:
        booking_status = filters.get("booking_status")
        if booking_status is not None and str(booking_status).strip() in {"", "0", "ALL", "all"}:
            filters["booking_status"] = None
        items, total = self.repository.list_all_bookings(**filters)
        return PaginatedResponse[BookingResponse].build(
            items=[BookingResponse.from_model(item) for item in items],
            total=total,
            page=filters["page"],
            page_size=filters["page_size"],
        )

    def admin_update_status(self, booking_id: int, booking_status: str, location_code: str, notes: str | None) -> BookingStatusResponse:
        require_notes_for_completion(booking_status, notes)
        booking = self.guards.require_existing_for_location(booking_id, location_code)
        booking = self.repository.update_status(booking, booking_status, notes)
        self.notifications.notify(
            booking.user_id,
            "Booking updated",
            f"Your booking is now {booking_status.lower()}.",
            "schedule_change",
            {"booking_id": booking.id},
        )
        return BookingStatusResponse.from_model(booking)

    def trainer_update_status(self, trainer_id: int, booking_id: int, booking_status: str, location_code: str, notes: str | None) -> BookingStatusResponse:
        require_notes_for_completion(booking_status, notes)
        booking = self.guards.require_existing_for_location(booking_id, location_code, trainer_id=trainer_id)
        booking = self.repository.update_status(booking, booking_status, notes)
        self.notifications.notify(
            booking.user_id,
            "Booking updated",
            f"Your booking is now {booking_status.lower()}.",
            "schedule_change",
            {"booking_id": booking.id},
        )
        return BookingStatusResponse.from_model(booking)

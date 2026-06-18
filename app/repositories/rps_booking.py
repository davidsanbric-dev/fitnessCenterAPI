from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain import BookingStatus
from app.models import (
    Booking,
    ClassType,
    Discipline,
    Slot,
    Trainer,
    User,
)


# Adapted repository from clinic ScheduleAppointment/ScheduleServiceAppointment/GetAgenda/GetAppointment contracts.
class BookingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_slot_for_trainer_booking(
        self,
        booking_datetime: datetime,
        trainer_code: int,
        discipline_code: str,
    ) -> Slot | None:
        # Adapted slot resolution for ScheduleAppointment-style bookings.
        normalized_discipline = discipline_code.strip()
        discipline_id: int | None = None
        if normalized_discipline.isdigit():
            discipline_id = int(normalized_discipline)

        # Bookings carry minute resolution (date + HH:MM), so match the slot
        # within its minute rather than on an exact timestamp, which may hold
        # sub-minute precision.
        statement = (
            select(Slot)
            .join(Slot.trainer)
            .join(Slot.discipline)
            .where(
                Slot.slot_datetime >= booking_datetime,
                Slot.slot_datetime < booking_datetime + timedelta(minutes=1),
                Slot.is_available.is_(True),
                (Trainer.trainer_code == trainer_code) | (Trainer.id == trainer_code),
            )
        )

        if discipline_id is None:
            statement = statement.where(Discipline.discipline_code == normalized_discipline)
        else:
            statement = statement.where(Discipline.id == discipline_id)
        return self.db.scalar(statement)

    def get_slot_for_class_type_booking(
        self,
        booking_datetime: datetime,
        trainer_code: int,
        class_type_id: int,
        slot_assignment_code: str,
    ) -> Slot | None:
        # Adapted slot resolution for ScheduleServiceAppointment-style bookings.
        # Match within the booking's minute (see get_slot_for_trainer_booking).
        statement = (
            select(Slot)
            .join(Slot.trainer)
            .join(Slot.class_type)
            .where(
                Slot.slot_datetime >= booking_datetime,
                Slot.slot_datetime < booking_datetime + timedelta(minutes=1),
                Slot.is_available.is_(True),
                (Trainer.trainer_code == trainer_code) | (Trainer.id == trainer_code),
                ClassType.id == class_type_id,
                Slot.slot_assignment_code == slot_assignment_code,
            )
        )
        return self.db.scalar(statement)

    def create_booking(self, booking: Booking, slot: Slot | None = None) -> Booking:
        self.db.add(booking)
        if slot is not None:
            slot.is_available = False
        self.db.commit()
        self.db.refresh(booking)
        return self.get_booking(booking.id)

    def user_has_booking_at(self, user_id: int, booking_datetime: datetime) -> bool:
        statement = select(func.count()).select_from(Booking).where(
            Booking.user_id == user_id,
            Booking.booking_datetime == booking_datetime,
            Booking.booking_status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
        )
        return bool(self.db.scalar(statement))

    def list_bookings(
        self,
        user_id: int,
        booking_status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        trainer_id: int | None = None,
        discipline_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Booking], int]:
        statement = self._base_booking_statement(user_id)
        count_statement = select(func.count()).select_from(Booking).where(Booking.user_id == user_id)
        if booking_status:
            statement = statement.where(Booking.booking_status == booking_status)
            count_statement = count_statement.where(Booking.booking_status == booking_status)
        if date_from is not None:
            statement = statement.where(Booking.booking_datetime >= date_from)
            count_statement = count_statement.where(Booking.booking_datetime >= date_from)
        if date_to is not None:
            statement = statement.where(Booking.booking_datetime <= date_to)
            count_statement = count_statement.where(Booking.booking_datetime <= date_to)
        if trainer_id is not None:
            statement = statement.where(Booking.trainer_id == trainer_id)
            count_statement = count_statement.where(Booking.trainer_id == trainer_id)
        if discipline_id is not None:
            statement = statement.where(Booking.discipline_id == discipline_id)
            count_statement = count_statement.where(Booking.discipline_id == discipline_id)
        total = int(self.db.scalar(count_statement) or 0)
        ordered = statement.order_by(Booking.booking_datetime.desc())
        # page_size == 0 means "no pagination": return every matching row.
        if page_size > 0:
            ordered = ordered.offset((page - 1) * page_size).limit(page_size)
        items = self.db.scalars(ordered).all()
        return list(items), total

    def _base_booking_statement(self, user_id: int):
        return (
            select(Booking)
            .options(
                selectinload(Booking.user).selectinload(User.profile),
                selectinload(Booking.trainer).selectinload(Trainer.disciplines),
                selectinload(Booking.class_type),
                selectinload(Booking.category),
            )
            .where(Booking.user_id == user_id)
        )

    def get_booking(self, booking_id: int) -> Booking | None:
        statement = (
            select(Booking)
            .options(
                selectinload(Booking.user).selectinload(User.profile),
                selectinload(Booking.trainer).selectinload(Trainer.disciplines),
                selectinload(Booking.class_type),
                selectinload(Booking.category),
            )
            .where(Booking.id == booking_id)
        )
        return self.db.scalar(statement)

    def update_status(self, booking: Booking, booking_status: str, notes: str | None) -> Booking:
        # Adapted from clinic UpdateAppointmentStatus behavior and slot release rules.
        booking.booking_status = booking_status
        booking.notes = notes or booking.notes
        if booking.slot is not None and booking_status == BookingStatus.CANCELLED:
            booking.slot.is_available = True
        self.db.commit()
        self.db.refresh(booking)
        return self.get_booking(booking.id) or booking

    def list_upcoming(self, user_id: int, limit: int = 5) -> list[Booking]:
        statement = self._base_booking_statement(user_id).where(Booking.booking_datetime >= datetime.utcnow()).order_by(Booking.booking_datetime).limit(limit)
        return list(self.db.scalars(statement).all())

    def list_all_bookings(
        self,
        booking_status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        trainer_id: int | None = None,
        discipline_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Booking], int]:
        statement = (
            select(Booking)
            .options(
                selectinload(Booking.user).selectinload(User.profile),
                selectinload(Booking.trainer).selectinload(Trainer.disciplines),
                selectinload(Booking.class_type),
                selectinload(Booking.category),
            )
        )
        count_statement = select(func.count()).select_from(Booking)

        if booking_status:
            statement = statement.where(Booking.booking_status == booking_status)
            count_statement = count_statement.where(Booking.booking_status == booking_status)
        if date_from is not None:
            statement = statement.where(Booking.booking_datetime >= date_from)
            count_statement = count_statement.where(Booking.booking_datetime >= date_from)
        if date_to is not None:
            statement = statement.where(Booking.booking_datetime <= date_to)
            count_statement = count_statement.where(Booking.booking_datetime <= date_to)
        if trainer_id is not None:
            statement = statement.where(Booking.trainer_id == trainer_id)
            count_statement = count_statement.where(Booking.trainer_id == trainer_id)
        if discipline_id is not None:
            statement = statement.where(Booking.discipline_id == discipline_id)
            count_statement = count_statement.where(Booking.discipline_id == discipline_id)

        total = int(self.db.scalar(count_statement) or 0)
        items = self.db.scalars(
            statement.order_by(Booking.booking_datetime.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return list(items), total

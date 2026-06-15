from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.schemas import APIModel

if TYPE_CHECKING:
    from app.models import Booking, ClassCategory, ClassType, Location, User


# Adapted trainer node from clinic Professional nested in appointment DTOs.
class BookingTrainerInfo(APIModel):
    trainer_id: int
    full_name: str
    discipline_id: int | None = None
    discipline_name: str | None = None

    @classmethod
    def from_booking(cls, booking: Booking) -> BookingTrainerInfo:
        # Full-booking projection: prefer the trainer's primary discipline, then
        # fall back to the booking's own discipline fields.
        trainer = booking.trainer
        discipline = trainer.disciplines[0] if trainer.disciplines else None
        return cls(
            trainer_id=trainer.id,
            full_name=trainer.full_name,
            discipline_id=discipline.id if discipline else booking.discipline_id,
            discipline_name=discipline.name if discipline else booking.discipline.name if booking.discipline else None,
        )

    @classmethod
    def from_upcoming(cls, booking: Booking) -> BookingTrainerInfo:
        # Upcoming/home projection: discipline comes straight from the booking.
        discipline = booking.discipline
        return cls(
            trainer_id=booking.trainer.id,
            full_name=booking.trainer.full_name,
            discipline_id=discipline.id if discipline else None,
            discipline_name=discipline.name if discipline else None,
        )


class BookingClassTypeInfo(APIModel):
    # Adapted service node from clinic Service nested in appointment DTOs.
    class_type_id: int
    name: str
    type_name: str | None = None

    @classmethod
    def from_model(cls, class_type: ClassType) -> BookingClassTypeInfo:
        return cls(class_type_id=class_type.id, name=class_type.name, type_name=class_type.schedule_type)


class BookingCategoryInfo(APIModel):
    # Adapted group node from clinic Group nested in appointment DTOs.
    category_id: int
    name: str

    @classmethod
    def from_model(cls, category: ClassCategory) -> BookingCategoryInfo:
        return cls(category_id=category.id, name=category.name)


class BookingLocationInfo(APIModel):
    # Adapted branch node from clinic Branch nested in appointment DTOs.
    location_id: int
    name: str
    location_code: str | None = None

    @classmethod
    def from_model(cls, location: Location) -> BookingLocationInfo:
        return cls(location_id=location.id, name=location.name, location_code=location.location_code)


class BookingMemberInfo(APIModel):
    # The member who owns the booking, surfaced for staff/trainer agenda views
    # (the member's own views simply show themselves here).
    user_id: int
    full_name: str
    email: str | None = None

    @classmethod
    def from_user(cls, user: User) -> BookingMemberInfo:
        profile = user.profile
        full_name = (
            " ".join(filter(None, [profile.first_name, profile.paternal_surname, profile.maternal_surname])).strip()
            if profile is not None
            else ""
        ) or user.email
        return cls(user_id=user.id, full_name=full_name, email=user.email)


class BookingByTrainerCreate(APIModel):
    # Adapted from clinic ScheduleAppointmentCommand -> gym by-trainer booking payload.
    booking_date: str
    booking_time: str
    location_code: str
    session_duration_minutes: int
    discipline_code: str
    trainer_code: int
    notes: str | None = None


class BookingByClassTypeCreate(APIModel):
    # Adapted from clinic ScheduleServiceAppointmentCommand -> gym by-class-type payload.
    booking_date: str
    booking_time: str
    location_code: str
    trainer_code: int
    slot_assignment_code: str
    class_type_id: int
    notes: str | None = None


class BookingStatusUpdate(APIModel):
    # Adapted from clinic UpdateAppointmentStatusCommand.
    booking_status: str
    location_code: str
    notes: str | None = None


class BookingStatusResponse(APIModel):
    # Adapted booking status mutation response.
    booking_id: int
    booking_status: str
    updated_at: datetime

    @classmethod
    def from_model(cls, booking: Booking) -> BookingStatusResponse:
        return cls(booking_id=booking.id, booking_status=booking.booking_status, updated_at=booking.updated_at)


class BookingResponse(APIModel):
    # Adapted from clinic GetAgenda/GetAppointment DTOs -> gym booking projection.
    booking_id: int
    booking_status: str
    booking_datetime: datetime
    scheduled_at: datetime
    session_duration_minutes: int | None = None
    preparation_info: str | None = None
    has_pdf: bool
    pdf_code: str | None = None
    notes: str | None = None
    is_overbooking: bool
    member: BookingMemberInfo | None = None
    trainer: BookingTrainerInfo | None = None
    class_type: BookingClassTypeInfo | None = None
    category: BookingCategoryInfo | None = None
    location: BookingLocationInfo | None = None

    @classmethod
    def from_model(cls, booking: Booking) -> BookingResponse:
        return cls(
            booking_id=booking.id,
            booking_status=booking.booking_status,
            booking_datetime=booking.booking_datetime,
            scheduled_at=booking.scheduled_at,
            session_duration_minutes=booking.session_duration_minutes,
            preparation_info=booking.preparation_info,
            has_pdf=booking.has_pdf,
            pdf_code=booking.pdf_code,
            notes=booking.notes,
            is_overbooking=booking.is_overbooking,
            member=BookingMemberInfo.from_user(booking.user) if booking.user is not None else None,
            trainer=BookingTrainerInfo.from_booking(booking) if booking.trainer else None,
            class_type=BookingClassTypeInfo.from_model(booking.class_type) if booking.class_type else None,
            category=BookingCategoryInfo.from_model(booking.category) if booking.category else None,
            location=BookingLocationInfo.from_model(booking.location) if booking.location else None,
        )


class UpcomingBookingResponse(APIModel):
    # Adapted home-facing subset of agenda/upcoming appointments.
    booking_id: int
    booking_datetime: datetime
    class_type: BookingClassTypeInfo | None = None
    trainer: BookingTrainerInfo | None = None
    booking_status: str

    @classmethod
    def from_model(cls, booking: Booking) -> UpcomingBookingResponse:
        return cls(
            booking_id=booking.id,
            booking_datetime=booking.booking_datetime,
            class_type=BookingClassTypeInfo.from_model(booking.class_type) if booking.class_type else None,
            trainer=BookingTrainerInfo.from_upcoming(booking) if booking.trainer else None,
            booking_status=booking.booking_status,
        )

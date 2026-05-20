from __future__ import annotations

from datetime import datetime

from app.schemas import APIModel


# Adapted trainer node from clinic Professional nested in appointment DTOs.
class BookingTrainerInfo(APIModel):
    trainer_id: int
    full_name: str
    discipline_id: int | None = None
    discipline_name: str | None = None


class BookingClassTypeInfo(APIModel):
    # Adapted service node from clinic Service nested in appointment DTOs.
    class_type_id: int
    name: str
    type_name: str | None = None


class BookingCategoryInfo(APIModel):
    # Adapted group node from clinic Group nested in appointment DTOs.
    category_id: int
    name: str


class BookingLocationInfo(APIModel):
    # Adapted branch node from clinic Branch nested in appointment DTOs.
    location_id: int
    name: str
    location_code: str | None = None


class BookingByTrainerCreate(APIModel):
    # Adapted from clinic ScheduleAppointmentCommand -> gym by-trainer booking payload.
    booking_date: str
    booking_time: str
    location_code: str
    session_duration_minutes: int
    discipline_code: str
    trainer_code: int
    is_online: bool = False
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


class BookingResponse(APIModel):
    # Adapted from clinic GetAgenda/GetAppointment DTOs -> gym booking projection.
    booking_id: int
    booking_status: str
    booking_datetime: datetime
    scheduled_at: datetime
    session_duration_minutes: int | None = None
    is_online: bool
    online_session_url: str | None = None
    preparation_info: str | None = None
    has_pdf: bool
    pdf_code: str | None = None
    notes: str | None = None
    is_overbooking: bool
    trainer: BookingTrainerInfo | None = None
    class_type: BookingClassTypeInfo | None = None
    category: BookingCategoryInfo | None = None
    location: BookingLocationInfo | None = None


class UpcomingBookingResponse(APIModel):
    # Adapted home-facing subset of agenda/upcoming appointments.
    booking_id: int
    booking_datetime: datetime
    class_type: BookingClassTypeInfo | None = None
    trainer: BookingTrainerInfo | None = None
    booking_status: str
    is_online: bool

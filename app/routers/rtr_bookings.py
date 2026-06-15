from __future__ import annotations

from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.scm_booking import (
    BookingByClassTypeCreate,
    BookingByTrainerCreate,
    BookingResponse,
    BookingStatusResponse,
    BookingStatusUpdate,
)
from app.schemas import PaginatedResponse
from app.services.svc_booking import BookingService

router = APIRouter(prefix="/bookings", tags=["bookings"])


# Adapted Path A from clinic ScheduleAppointmentCommand.
@router.post("/by-trainer", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_by_trainer(payload: BookingByTrainerCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return BookingService(db).create_by_trainer(current_user, payload)


# Adapted Path B from clinic ScheduleServiceAppointmentCommand.
@router.post("/by-class-type", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_by_class_type(payload: BookingByClassTypeCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return BookingService(db).create_by_class_type(current_user, payload)


# Adapted from clinic GetAgenda query.
@router.get("", response_model=PaginatedResponse[BookingResponse])
def list_bookings(
    booking_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    trainer_id: int | None = None,
    discipline_id: int | None = None,
    location_code: str | None = None,
    page: int = Query(default=1, ge=1),
    # page_size == 0 returns the full set unpaginated (used by the member's
    # training-history view, which paginates completed sessions client-side).
    page_size: int = Query(default=20, ge=0, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BookingService(db).list_bookings(
        current_user.id,
        booking_status=booking_status,
        date_from=date_from,
        date_to=date_to,
        trainer_id=trainer_id,
        discipline_id=discipline_id,
        location_code=location_code,
        page=page,
        page_size=page_size,
    )


# Adapted home-focused subset of agenda/upcoming bookings.
@router.get("/upcoming")
def upcoming_bookings(
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BookingService(db).upcoming(current_user.id, limit)


# Adapted from clinic GetAppointment query.
@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    location_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BookingService(db).get_booking(current_user.id, booking_id, location_code)


# Adapted from clinic UpdateAppointmentStatusCommand.
@router.patch("/{booking_id}/status", response_model=BookingStatusResponse)
def update_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BookingService(db).update_status(current_user.id, booking_id, payload.booking_status, payload.location_code, payload.notes)

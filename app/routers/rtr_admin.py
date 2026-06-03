from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.authorization import ensure_admin_or_manager
from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import PaginatedResponse
from app.schemas import MessageResponse
from app.schemas.scm_admin import AdminHomeResponse
from app.schemas.scm_booking import BookingResponse, BookingStatusResponse, BookingStatusUpdate
from app.schemas.scm_membership import AdminMembershipPlanUpsertRequest, MembershipPlanResponse
from app.services.svc_admin import AdminService
from app.services.svc_booking import BookingService
from app.services.svc_membership import MembershipService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/home", response_model=AdminHomeResponse)
def get_admin_home(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_admin_or_manager(db, current_user)
    return AdminService(db).get_home()


@router.get("/bookings", response_model=PaginatedResponse[BookingResponse])
def list_admin_bookings(
    booking_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    trainer_id: int | None = None,
    discipline_id: int | None = None,
    location_code: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_or_manager(db, current_user)
    return BookingService(db).list_all_bookings(
        booking_status=booking_status,
        date_from=date_from,
        date_to=date_to,
        trainer_id=trainer_id,
        discipline_id=discipline_id,
        location_code=location_code,
        page=page,
        page_size=page_size,
    )


@router.patch("/bookings/{booking_id}/status", response_model=BookingStatusResponse)
def update_admin_booking_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_or_manager(db, current_user)
    return BookingService(db).admin_update_status(
        booking_id=booking_id,
        booking_status=payload.booking_status,
        location_code=payload.location_code,
        notes=payload.notes,
    )


@router.post('/membership-plans', response_model=MembershipPlanResponse)
def create_admin_membership_plan(
    payload: AdminMembershipPlanUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_or_manager(db, current_user)
    return MembershipService(db).create_plan(payload)


@router.put('/membership-plans/{plan_id}', response_model=MembershipPlanResponse)
def update_admin_membership_plan(
    plan_id: int,
    payload: AdminMembershipPlanUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_or_manager(db, current_user)
    return MembershipService(db).update_plan(plan_id, payload)


@router.delete('/membership-plans/{plan_id}', response_model=MessageResponse)
def delete_admin_membership_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_admin_or_manager(db, current_user)
    return MembershipService(db).delete_plan(plan_id)

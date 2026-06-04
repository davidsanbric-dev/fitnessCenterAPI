from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import PaginatedResponse
from app.schemas.scm_booking import BookingResponse
from app.schemas.scm_trainer import (
    TrainerAvailabilityResponse,
    TrainerDashboardResponse,
    TrainerDetailResponse,
    TrainerMeProfileResponse,
    TrainerMeProfileUpdate,
    TrainerSlotCreate,
    TrainerSlotResponse,
    TrainerSlotUpdate,
    TrainerSummary,
)
from app.services.svc_booking import BookingService
from app.services.svc_trainer import TrainerService

# Authentication is required so the request is scoped to the caller's company
# (the dependency also establishes the tenant filter on the DB session).
router = APIRouter(prefix="/trainers", tags=["trainers"], dependencies=[Depends(get_current_user)])


# Adapted from clinic GetProfessionalsByPrevision listing with mapped filter names.
@router.get("", response_model=PaginatedResponse[TrainerSummary])
def list_trainers(
    discipline_id: int | None = None,
    membership_plan_id: int | None = None,
    location_code: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return TrainerService(db).list_trainers(
        discipline_id=discipline_id,
        membership_plan_id=membership_plan_id,
        location_code=location_code,
        search=search,
        page=page,
        page_size=page_size,
    )


# ---- Trainer self-service ("me") ----------------------------------------------
# These resolve the Trainer record from the signed-in user, so a trainer is
# scoped to its own personal data, slots and bookings. Declared before the
# ``/{trainer_id}`` routes so "me" is never parsed as a numeric id.


@router.get("/me", response_model=TrainerMeProfileResponse)
def get_my_trainer_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TrainerService(db).get_my_profile(current_user)


@router.put("/me", response_model=TrainerMeProfileResponse)
def update_my_trainer_profile(
    payload: TrainerMeProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return TrainerService(db).update_my_profile(current_user, payload.model_dump(exclude_unset=True))


@router.get("/me/dashboard", response_model=TrainerDashboardResponse)
def get_my_trainer_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TrainerService(db).get_my_dashboard(current_user)


@router.get("/me/slots", response_model=PaginatedResponse[TrainerSlotResponse])
def list_my_slots(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = TrainerService(db).list_my_slots(current_user)
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/me/slots", response_model=TrainerSlotResponse, status_code=status.HTTP_201_CREATED)
def create_my_slot(
    payload: TrainerSlotCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return TrainerService(db).create_my_slot(current_user, payload.model_dump())


@router.patch("/me/slots/{slot_id}", response_model=TrainerSlotResponse)
def update_my_slot(
    slot_id: int,
    payload: TrainerSlotUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return TrainerService(db).update_my_slot(current_user, slot_id, payload.model_dump(exclude_unset=True))


@router.delete("/me/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_slot(slot_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    TrainerService(db).delete_my_slot(current_user, slot_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me/bookings", response_model=PaginatedResponse[BookingResponse])
def list_my_bookings(
    booking_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Scope the admin booking listing to the signed-in trainer's own trainer id.
    trainer = TrainerService(db)._require_self(current_user)
    return BookingService(db).list_all_bookings(
        booking_status=booking_status,
        date_from=date_from,
        date_to=date_to,
        trainer_id=trainer.id,
        discipline_id=None,
        location_code=None,
        page=page,
        page_size=page_size,
    )


# Adapted trainer detail projection from clinic professional detail context.
@router.get("/{trainer_id}", response_model=TrainerDetailResponse)
def get_trainer(trainer_id: int, db: Session = Depends(get_db)):
    return TrainerService(db).get_trainer(trainer_id)


# Adapted from clinic professional availability window query.
@router.get("/{trainer_id}/availability", response_model=TrainerAvailabilityResponse)
def get_trainer_availability(
    trainer_id: int,
    date_from: datetime,
    date_to: datetime,
    discipline_id: int | None = None,
    db: Session = Depends(get_db),
):
    return TrainerService(db).get_availability(trainer_id, date_from, date_to, discipline_id)

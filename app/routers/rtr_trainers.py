from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas import PaginatedResponse
from app.schemas.scm_trainer import TrainerAvailabilityResponse, TrainerDetailResponse, TrainerSummary
from app.services.svc_trainer import TrainerService

router = APIRouter(prefix="/trainers", tags=["trainers"])


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

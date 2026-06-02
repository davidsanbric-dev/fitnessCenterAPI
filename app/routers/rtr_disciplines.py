from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.schemas import PaginatedResponse
from app.schemas.scm_discipline import DisciplineAvailabilityResponse, DisciplineDetailResponse, DisciplineSummary
from app.services.svc_discipline import DisciplineService

# Auth required so disciplines are scoped to the caller's company.
router = APIRouter(prefix="/disciplines", tags=["disciplines"], dependencies=[Depends(get_current_user)])


# Adapted from clinic specialty catalog listing.
@router.get("", response_model=PaginatedResponse[DisciplineSummary])
def list_disciplines(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return DisciplineService(db).list_disciplines(search, page, page_size)


# Adapted discipline detail from clinic specialty + professionals projection.
@router.get("/{discipline_id}", response_model=DisciplineDetailResponse)
def get_discipline(discipline_id: int, db: Session = Depends(get_db)):
    return DisciplineService(db).get_discipline(discipline_id)


# Adapted from clinic professionals-by-specialty query.
@router.get("/{discipline_id}/trainers")
def get_discipline_trainers(
    discipline_id: int,
    membership_plan_id: int | None = None,
    location_code: str | None = None,
    db: Session = Depends(get_db),
):
    return DisciplineService(db).get_trainers(discipline_id, membership_plan_id, location_code)


# Adapted from clinic GetAvailableAppointments filtered by specialty/discipline.
@router.get("/{discipline_id}/availability", response_model=DisciplineAvailabilityResponse)
def get_discipline_availability(
    discipline_id: int,
    date_from: datetime,
    date_to: datetime,
    session_duration_minutes: int | None = None,
    trainer_id: int | None = None,
    is_online: bool | None = None,
    location_code: str | None = None,
    db: Session = Depends(get_db),
):
    return DisciplineService(db).get_availability(discipline_id, date_from, date_to, trainer_id, is_online, location_code)

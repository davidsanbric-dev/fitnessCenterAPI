from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.schemas import PaginatedResponse
from app.schemas.scm_slot import SlotResponse
from app.services.svc_slot import SlotService

# Auth required so slot search is scoped to the caller's company.
router = APIRouter(prefix="/slots", tags=["slots"], dependencies=[Depends(get_current_user)])


# Adapted unified slot search endpoint over clinic appointment/service-appointment availability contracts.
@router.get("", response_model=PaginatedResponse[SlotResponse])
def search_slots(
    date_from: datetime,
    date_to: datetime,
    trainer_id: int | None = None,
    discipline_id: int | None = None,
    discipline_code: str | None = None,
    class_type_id: int | None = None,
    query_type: str | None = None,
    session_duration_minutes: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return SlotService(db).search_slots(
        date_from=date_from,
        date_to=date_to,
        trainer_id=trainer_id,
        discipline_id=discipline_id,
        discipline_code=discipline_code,
        class_type_id=class_type_id,
        query_type=query_type,
        session_duration_minutes=session_duration_minutes,
        page=page,
        page_size=page_size,
    )

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.schemas.scm_static import StaticConfigResponse
from app.services.svc_static import StaticService

# Auth required so the returned locations are scoped to the caller's company.
router = APIRouter(tags=["statics"], dependencies=[Depends(get_current_user)])


# Adapted directly from clinic GetStatic contract.
@router.get("/statics", response_model=StaticConfigResponse)
def get_statics(db: Session = Depends(get_db)):
    return StaticService(db).get_statics()

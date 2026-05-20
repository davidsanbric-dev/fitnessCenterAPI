from __future__ import annotations

from fastapi import APIRouter

from app.schemas.scm_static import StaticConfigResponse
from app.services.svc_static import StaticService

router = APIRouter(tags=["statics"])


# Adapted directly from clinic GetStatic contract.
@router.get("/statics", response_model=StaticConfigResponse)
def get_statics():
    return StaticService().get_statics()

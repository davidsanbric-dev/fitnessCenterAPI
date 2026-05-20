from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.scm_home import HomeResponse
from app.services.svc_home import HomeService

router = APIRouter(tags=["home"])


# Adapted composite endpoint analogous to clinic home composition (agenda + static) with gym enrichments.
@router.get("/home", response_model=HomeResponse)
def get_home(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return HomeService(db).get_home(current_user)

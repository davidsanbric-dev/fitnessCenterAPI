from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.scm_membership import CurrentMembershipResponse, MembershipPlanDetailResponse, MembershipPlanResponse
from app.services.svc_membership import MembershipService

router = APIRouter(tags=["memberships"])


# Adapted clinic prevision concept promoted to gym plan catalog.
@router.get("/membership-plans")
def list_membership_plans(db: Session = Depends(get_db)):
    return MembershipService(db).list_plans()


# Adapted membership detail endpoint over prevision-like entity.
@router.get("/membership-plans/{plan_id}", response_model=MembershipPlanDetailResponse)
def get_membership_plan(plan_id: int, db: Session = Depends(get_db)):
    return MembershipService(db).get_plan(plan_id)


# Adapted member-prevision linkage as current membership read endpoint.
@router.get("/users/me/membership", response_model=CurrentMembershipResponse)
def get_current_membership(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MembershipService(db).get_current_membership(current_user.id)

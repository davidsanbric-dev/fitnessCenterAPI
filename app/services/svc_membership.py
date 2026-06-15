from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.models import MembershipPlan
from app.repositories.rps_membership import MembershipRepository
from app.schemas.scm_membership import (
    AdminMembershipPlanUpsertRequest,
    CurrentMembershipResponse,
    MembershipPlanDetailResponse,
    MembershipPlanResponse,
)
from app.services.svc_common import get_or_404


class MembershipService:
    def __init__(self, db: Session):
        self.repository = MembershipRepository(db)

    def _validate_unique_plan_name(self, name: str, *, current: MembershipPlan | None = None) -> None:
        if current is not None and name == current.name:
            return
        if self.repository.get_by_name(name):
            raise ConflictException("Membership plan name already exists")

    def list_plans(self) -> dict:
        plans = self.repository.list_plans()
        return {"items": [MembershipPlanResponse.from_model(plan) for plan in plans]}

    def get_plan(self, plan_id: int) -> MembershipPlanDetailResponse:
        plan = get_or_404(self.repository.get_plan(plan_id), "Membership plan not found")
        return MembershipPlanDetailResponse.from_model(plan)

    def get_current_membership(self, user_id: int) -> CurrentMembershipResponse:
        membership = get_or_404(self.repository.get_user_membership(user_id), "Membership not found")
        return CurrentMembershipResponse.from_model(membership)

    def create_plan(self, payload: AdminMembershipPlanUpsertRequest) -> MembershipPlanResponse:
        self._validate_unique_plan_name(payload.name)

        plan = self.repository.create_plan(MembershipPlan(**payload.model_dump()))
        return MembershipPlanResponse.from_model(plan)

    def update_plan(self, plan_id: int, payload: AdminMembershipPlanUpsertRequest) -> MembershipPlanResponse:
        plan = get_or_404(self.repository.get_plan(plan_id), "Membership plan not found")

        self._validate_unique_plan_name(payload.name, current=plan)

        updated = self.repository.update_plan(plan, payload.model_dump())
        return MembershipPlanResponse.from_model(updated)

    def delete_plan(self, plan_id: int) -> dict:
        plan = get_or_404(self.repository.get_plan(plan_id), "Membership plan not found")

        if self.repository.has_dependencies(plan_id):
            raise ConflictException("Cannot delete membership plan with active references")

        self.repository.delete_plan(plan)
        return {"message": "Membership plan deleted"}

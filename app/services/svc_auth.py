from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.authorization import resolve_role_permissions
from app.core.client_origin import ClientOrigin
from app.core.config import ALLOWED_ROLES_BY_ORIGIN, settings
from app.core.exceptions import UnauthorizedException
from app.core.firebase_auth import set_firebase_custom_claims
from app.domain import Rut, enforce_origin_login_allowed
from app.core.tenancy import set_session_company
from app.models import (
    MemberProfile,
    User,
)
from app.repositories.rps_membership import MembershipRepository
from app.repositories.rps_user import UserRepository
from app.schemas.scm_auth import AppUserContext, FirebaseLoginResponse, RegisterResponse
from app.schemas.scm_user import CurrentUserResponse
from app.services.svc_company import CompanyService
from app.services.validators import AuthGuards


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)
        self.membership_repository = MembershipRepository(db)
        self.company_service = CompanyService(db)
        self.guards = AuthGuards(self.user_repository)

    def register(self, payload) -> RegisterResponse:
        self.guards.require_email_available(payload.email)

        company = self.company_service.resolve_registration_company(getattr(payload, "company", None))
        set_session_company(self.db, company.id)

        user = User(email=str(payload.email))
        profile = self._build_member_profile(payload)
        user = self.user_repository.create_user(user, profile)
        basic_plan = self.membership_repository.get_default_plan()
        if basic_plan is not None:
            self.membership_repository.create_default_membership(user.id, basic_plan)
            user = self.user_repository.get_by_id(user.id) or user
        return RegisterResponse.from_model(user)

    @staticmethod
    def _build_member_profile(payload) -> MemberProfile:
        birth_date = date.fromisoformat(payload.birth_date) if payload.birth_date else None
        # Registration does not collect a RUT, so derive a stable, well-formed one
        # from the member's email (same scheme as the seed/backfill). Without this
        # every self-registered member would have a null RUT, which surfaces as
        # "Not available" in the booking-details dialog.
        rut = str(Rut.deterministic_for(str(payload.email)))
        return MemberProfile(
            rut=rut,
            first_name=payload.first_name,
            paternal_surname=payload.paternal_surname,
            maternal_surname=payload.maternal_surname,
            mobile_phone=payload.mobile_phone,
            landline_phone=payload.landline_phone,
            birth_date=birth_date,
            address=payload.address,
        )

    def get_profile(self, user_id: int) -> CurrentUserResponse:
        return CurrentUserResponse.from_model(self.guards.require_user_with_profile(user_id))

    def update_profile(self, user_id: int, payload: dict) -> CurrentUserResponse:
        user = self.guards.require_user_with_profile(user_id)
        updated = self.user_repository.update_profile(user, payload)
        return CurrentUserResponse.from_model(updated)

    def firebase_login(self, id_token: str, *, origin: ClientOrigin) -> FirebaseLoginResponse:
        from app.core.firebase_auth import verify_firebase_token

        payload = verify_firebase_token(id_token)
        firebase_uid = str(payload.get("uid") or "").strip()
        email = str(payload.get("email") or "").strip().lower()

        if not firebase_uid or not email:
            raise UnauthorizedException("Invalid Firebase token")

        user = self.guards.require_provisioned_user(email)

        role, permissions = resolve_role_permissions(user)

        enforce_origin_login_allowed(role, ALLOWED_ROLES_BY_ORIGIN[origin])

        context = AppUserContext.from_user(user, role, permissions)

        display_name = " ".join(
            part
            for part in [context.profile["first_name"], context.profile["last_name"]]
            if part
        ).strip()
        claims = {
            "app_user_id": user.id,
            "app_email": user.email,
            "app_role": role,
            "app_is_active": user.is_active,
            "app_display_name": display_name or None,
        }
        set_firebase_custom_claims(firebase_uid, claims)

        return FirebaseLoginResponse(
            access_token=id_token,
            refresh_token="",
            token_type="Bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=context,
        )

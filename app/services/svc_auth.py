from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.client_origin import ClientOrigin
from app.core.config import settings
from app.core.firebase_auth import set_firebase_custom_claims
from app.core.tenancy import set_session_company
from app.models import (
    MemberMembership,
    MemberProfile,
    MembershipPlan,
    TargetCompany,
    User,
)
from app.repositories.rps_user import UserRepository
from app.services.svc_common import serialize_user


# Adapted service from clinic RegisterPatient/GetPatient workflows to JWT-based gym auth/profile flows.
class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)

    def _resolve_registration_company(self, slug: str | None) -> TargetCompany:
        # Self-registration carries no logged-in tenant, so the target company
        # must be resolved explicitly. TargetCompany is not tenant-scoped, so
        # this query is never filtered.
        companies = list(self.db.scalars(select(TargetCompany)).all())
        if slug:
            wanted = slug.strip().lower()
            for company in companies:
                if company.slug.lower() == wanted:
                    return company
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown company")
        if len(companies) == 1:
            return companies[0]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="company is required")

    def register(self, payload) -> dict:
        # Adapted from clinic RegisterPatient command; provisions the backend record while Firebase owns the credential.
        # Email uniqueness is global, so this check must run before the tenant is
        # set (otherwise it would only see the resolved company's users).
        if self.user_repository.get_by_email(payload.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        # Scope the session to the chosen company so the default-plan lookup and
        # all new rows (user, profile, membership) are confined to it.
        company = self._resolve_registration_company(getattr(payload, "company", None))
        set_session_company(self.db, company.id)

        user = User(email=str(payload.email))
        birth_date = date.fromisoformat(payload.birth_date) if payload.birth_date else None
        profile = MemberProfile(
            first_name=payload.first_name,
            paternal_surname=payload.paternal_surname,
            maternal_surname=payload.maternal_surname,
            mobile_phone=payload.mobile_phone,
            landline_phone=payload.landline_phone,
            birth_date=birth_date,
            address=payload.address,
        )
        user = self.user_repository.create_user(user, profile)
        basic_plan = self.db.query(MembershipPlan).order_by(MembershipPlan.price).first()
        if basic_plan is not None:
            membership = MemberMembership(
                user_id=user.id,
                membership_plan_id=basic_plan.id,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=basic_plan.duration_days),
                status="ACTIVE",
                bookings_used=0,
            )
            self.db.add(membership)
            self.db.commit()
            user = self.user_repository.get_by_id(user.id) or user
        # Provisioning only: authentication tokens are issued by Firebase, so we
        # return the created member identity rather than minting local JWTs.
        return serialize_user(user)

    def get_profile(self, user_id: int) -> dict:
        # Adapted from clinic GetPatient query projection.
        user = self.user_repository.get_by_id(user_id)
        if user is None or user.profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return serialize_user(user)

    def update_profile(self, user_id: int, payload: dict) -> dict:
        user = self.user_repository.get_by_id(user_id)
        if user is None or user.profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        updated = self.user_repository.update_profile(user, payload)
        return serialize_user(updated)

    # Permission sets keyed by the role name stored in the ``roles`` table. The
    # role catalogue and the per-user assignment both live in the database (see
    # the seed migration); this only maps a resolved role name to its grants.
    _PERMISSIONS_BY_ROLE: dict[str, list[str]] = {
        "admin": [
            "admin.dashboard.read",
            "bookings.read",
            "bookings.write",
            "schedule.read",
            "trainers.read",
            "disciplines.read",
            "memberships.read",
            "notifications.read",
        ],
        "manager": [
            "admin.dashboard.read",
            "bookings.read",
            "schedule.read",
            "trainers.read",
            "disciplines.read",
            "memberships.read",
        ],
        "member": ["member.home.read", "bookings.read", "bookings.write"],
        # The trainer signs into the web app but, unlike admin/manager, is scoped
        # to its own slots, bookings, profile and a home dashboard. The grants
        # below back those four web modules.
        "trainer": [
            "trainer.home.read",
            "schedule.read",
            "schedule.write",
            "bookings.read",
            "trainer.profile.read",
            "trainer.profile.write",
        ],
    }

    _STAFF_ROLES = frozenset({"admin", "manager"})

    def resolve_role_permissions(self, user: User) -> tuple[str, list[str]]:
        # Role is sourced from the database (``users.role_id`` -> ``roles.name``),
        # not from config. Editing demo_users.json no longer changes who is an
        # admin at runtime; role assignment is durable DB state. Users without an
        # assigned role (e.g. self-registered members) default to "member".
        role_name = (user.role.name if user.role else "") or "member"
        permissions = self._PERMISSIONS_BY_ROLE.get(role_name, self._PERMISSIONS_BY_ROLE["member"])
        return role_name, permissions

    def is_admin_or_manager(self, user: User) -> bool:
        role, _ = self.resolve_role_permissions(user)
        return role in self._STAFF_ROLES

    # Role buckets each deployed application is allowed to sign in as. The mobile
    # app serves members; the web app serves staff (admin/manager).
    _ALLOWED_ROLES_BY_ORIGIN: dict[ClientOrigin, frozenset[str]] = {
        ClientOrigin.MOBILE: frozenset({"member"}),
        ClientOrigin.WEB: frozenset({"admin", "manager", "trainer"}),
    }

    def firebase_login(self, id_token: str, *, origin: ClientOrigin) -> dict:
        from app.core.firebase_auth import verify_firebase_token

        payload = verify_firebase_token(id_token)
        firebase_uid = str(payload.get("uid") or "").strip()
        email = str(payload.get("email") or "").strip().lower()

        if not firebase_uid or not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Firebase token")

        user = self.user_repository.get_by_email(email)
        if user is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User authenticated with Firebase but not provisioned in backend")

        role, permissions = self.resolve_role_permissions(user)

        # Enforce that the account's role matches the application it is signing in
        # from (members -> mobile, staff -> web). This is a product/UX boundary,
        # not a privilege gate: role is resolved from the verified email above, so
        # a mismatched origin can only reject a login, never elevate one.
        if role not in self._ALLOWED_ROLES_BY_ORIGIN[origin]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is not allowed to sign in from this application",
            )

        profile = user.profile
        profile_payload = {
            "first_name": profile.first_name if profile else "",
            "last_name": " ".join(
                item
                for item in [
                    profile.paternal_surname if profile else "",
                    profile.maternal_surname if profile else "",
                ]
                if item
            ).strip(),
        }

        display_name = " ".join(
            part
            for part in [profile_payload["first_name"], profile_payload["last_name"]]
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

        return {
            "access_token": id_token,
            "refresh_token": "",
            "token_type": "Bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": role,
                "permissions": permissions,
                "profile": profile_payload,
            },
        }

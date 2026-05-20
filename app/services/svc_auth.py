from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.firebase_auth import set_firebase_custom_claims
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.models import (
    MemberMembership,
    MemberProfile,
    MembershipPlan,
    User,
)
from app.repositories.rps_user import UserRepository
from app.services.svc_common import serialize_user


# Adapted service from clinic RegisterPatient/GetPatient workflows to JWT-based gym auth/profile flows.
class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)

    def register(self, payload) -> dict:
        # Adapted from clinic RegisterPatient command.
        if self.user_repository.get_by_email(payload.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        try:
            validate_password_strength(payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        user = User(email=str(payload.email), password_hash=hash_password(payload.password))
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
        access_token, _ = create_access_token(user.id)
        refresh_token, refresh_expiry = create_refresh_token(user.id)
        self.user_repository.store_refresh_token(user.id, refresh_token, refresh_expiry)
        return {
            **serialize_user(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    def login(self, email: str, password: str) -> dict:
        user = self.user_repository.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        access_token, _ = create_access_token(user.id)
        refresh_token, refresh_expiry = create_refresh_token(user.id)
        self.user_repository.store_refresh_token(user.id, refresh_token, refresh_expiry)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    def refresh(self, refresh_token: str) -> dict:
        token_record = self.user_repository.get_refresh_token(refresh_token)
        if token_record is None or token_record.is_revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        try:
            payload = decode_token(refresh_token)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        self.user_repository.revoke_refresh_token(refresh_token)
        access_token, _ = create_access_token(int(payload["sub"]))
        new_refresh_token, refresh_expiry = create_refresh_token(int(payload["sub"]))
        self.user_repository.store_refresh_token(int(payload["sub"]), new_refresh_token, refresh_expiry)
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    def logout(self, user_id: int) -> None:
        self.user_repository.revoke_user_refresh_tokens(user_id)

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

    def change_password(self, user_id: int, current_password: str, new_password: str) -> None:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        try:
            validate_password_strength(new_password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        self.user_repository.update_password(user, hash_password(new_password))

    def sync_firebase_claims(self, email: str, firebase_uid: str) -> dict:
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email")

        user = self.user_repository.get_by_email(normalized_email)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        role = "member"
        profile = user.profile
        display_name_parts = []
        if profile is not None:
            display_name_parts = [
                profile.first_name.strip(),
                profile.paternal_surname.strip(),
                profile.maternal_surname.strip(),
            ]

        display_name = " ".join(part for part in display_name_parts if part)
        claims = {
            "app_user_id": user.id,
            "app_email": user.email,
            "app_role": role,
            "app_is_active": user.is_active,
            "app_display_name": display_name or None,
        }

        set_firebase_custom_claims(firebase_uid, claims)
        return {
            "email": user.email,
            "firebase_uid": firebase_uid,
            "claims": claims,
        }

    def resolve_role_permissions(self, email: str) -> tuple[str, list[str]]:
        normalized_email = email.strip().lower()
        admin_emails = {item.strip().lower() for item in settings.admin_emails}
        manager_emails = {item.strip().lower() for item in settings.manager_emails}

        if normalized_email in admin_emails:
            return (
                "admin",
                [
                    "admin.dashboard.read",
                    "bookings.read",
                    "bookings.write",
                    "schedule.read",
                    "trainers.read",
                    "disciplines.read",
                    "memberships.read",
                    "notifications.read",
                ],
            )

        if normalized_email in manager_emails:
            return (
                "manager",
                [
                    "admin.dashboard.read",
                    "bookings.read",
                    "schedule.read",
                    "trainers.read",
                    "disciplines.read",
                    "memberships.read",
                ],
            )

        return ("member", ["member.home.read", "bookings.read", "bookings.write"])

    def is_admin_or_manager(self, email: str) -> bool:
        role, _ = self.resolve_role_permissions(email)
        return role in {"admin", "manager"}

    def firebase_login(self, id_token: str) -> dict:
        from app.core.firebase_auth import verify_firebase_token

        payload = verify_firebase_token(id_token)
        firebase_uid = str(payload.get("uid") or "").strip()
        email = str(payload.get("email") or "").strip().lower()

        if not firebase_uid or not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Firebase token")

        user = self.user_repository.get_by_email(email)
        if user is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User authenticated with Firebase but not provisioned in backend")

        role, permissions = self.resolve_role_permissions(user.email)
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
            "location_codes": list(settings.locations.keys()),
        }

        claims = {
            "app_user_id": user.id,
            "app_email": user.email,
            "app_role": role,
            "app_is_active": user.is_active,
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

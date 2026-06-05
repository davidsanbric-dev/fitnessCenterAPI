from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import firebase_admin
from fastapi import HTTPException, status
from firebase_admin import auth, credentials

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_firebase_app() -> firebase_admin.App:
    if firebase_admin._apps:
        return firebase_admin.get_app()

    options: dict[str, str] = {}
    if settings.firebase_project_id:
        options["projectId"] = settings.firebase_project_id

    if settings.firebase_service_account_path:
        service_account_path = Path(settings.firebase_service_account_path)
        if not service_account_path.is_absolute():
            project_root = Path(__file__).resolve().parents[2]
            service_account_path = project_root / service_account_path
        cred = credentials.Certificate(str(service_account_path))
    else:
        cred = credentials.ApplicationDefault()

    return firebase_admin.initialize_app(cred, options or None)


def verify_firebase_token(token: str) -> dict:
    if not token or not token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        _get_firebase_app()
        decoded = auth.verify_id_token(token, check_revoked=True)
    except auth.ExpiredIdTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except auth.RevokedIdTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked") from exc
    except auth.InvalidIdTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Firebase token") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Firebase auth is not configured") from exc

    # Email-based identity/role resolution requires a verified email to prevent
    # spoofing an allowlisted (e.g. admin) address via an unverified sign-up.
    if decoded.get("email_verified") is not True:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")
    return decoded


def create_or_align_firebase_account(email: str, password: str) -> str:
    """Provision a Firebase credential for a staff-created account and return its uid.

    Showcase-style: the account is created (or aligned) with ``email_verified=True``
    so the new trainer can sign in immediately, without the email-verification step
    the login gate (``verify_firebase_token``) otherwise enforces. This mirrors the
    demo-account seeding in ``scripts/set_and_verify_demo_users.py`` but is callable
    at runtime from the admin trainer-creation flow. Idempotent: an existing account
    is realigned (password reset, marked verified) rather than duplicated.
    """
    if not email or not email.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing email")
    if not password or len(password) < 6:
        # Firebase rejects passwords shorter than 6 characters; surface a clean 400.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters")

    try:
        _get_firebase_app()
        try:
            user = auth.get_user_by_email(email)
        except auth.UserNotFoundError:
            return auth.create_user(email=email, password=password, email_verified=True).uid
        # Existing account: align it to the desired state so the credential is usable.
        auth.update_user(user.uid, password=password, email_verified=True)
        return user.uid
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Firebase auth is not configured") from exc


def set_firebase_custom_claims(uid: str, claims: dict) -> None:
    if not uid or not uid.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Firebase user id")

    try:
        _get_firebase_app()
        auth.set_custom_user_claims(uid, claims)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Firebase auth is not configured") from exc

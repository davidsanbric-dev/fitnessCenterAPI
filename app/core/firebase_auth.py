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


def set_firebase_custom_claims(uid: str, claims: dict) -> None:
    if not uid or not uid.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Firebase user id")

    try:
        _get_firebase_app()
        auth.set_custom_user_claims(uid, claims)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Firebase auth is not configured") from exc

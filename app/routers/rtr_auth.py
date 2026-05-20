from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.dependencies import bearer_scheme, get_current_user, get_db
from app.core.firebase_auth import verify_firebase_token
from app.models import User
from app.schemas import MessageResponse
from app.schemas.scm_auth import (
    AppUserContext,
    FirebaseLoginRequest,
    FirebaseLoginResponse,
    FirebaseClaimsSyncResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenRefreshRequest,
    TokenResponse,
)
from app.schemas.scm_user import ChangePasswordRequest, CurrentUserResponse, UpdateUserRequest
from app.services.svc_auth import AuthService

router = APIRouter(tags=["auth"])


# Adapted from clinic RegisterPatient write flow.
@router.post("/auth/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return AuthService(db).register(payload)


# Adapted from clinic identity-based login semantics to email/password auth.
@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return AuthService(db).login(str(payload.email), payload.password)


# Auth extension for refresh-token lifecycle in adapted gym backend.
@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(payload: TokenRefreshRequest, db: Session = Depends(get_db)):
    return AuthService(db).refresh(payload.refresh_token)


# Auth extension for refresh-token revocation.
@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    AuthService(db).logout(current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Adapted from clinic GetPatient read flow.
@router.get("/users/me", response_model=CurrentUserResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AuthService(db).get_profile(current_user.id)


# Adapted member profile update from clinic patient profile mutations.
@router.put("/users/me", response_model=CurrentUserResponse)
def update_me(payload: UpdateUserRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return AuthService(db).update_profile(current_user.id, data)


# Auth extension for password change operation.
@router.put("/users/me/password", response_model=MessageResponse)
def change_password(payload: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    AuthService(db).change_password(current_user.id, payload.current_password, payload.new_password)
    return {"message": "Password updated"}


@router.post("/auth/firebase/sync-claims", response_model=FirebaseClaimsSyncResponse)
def sync_firebase_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = verify_firebase_token(credentials.credentials)
    firebase_uid = str(payload.get("uid") or "").strip()
    email = str(payload.get("email") or "").strip()

    if not firebase_uid or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Firebase token")

    return AuthService(db).sync_firebase_claims(email=email, firebase_uid=firebase_uid)


@router.post("/auth/firebase-login", response_model=FirebaseLoginResponse)
def firebase_login(payload: FirebaseLoginRequest, db: Session = Depends(get_db)):
    return AuthService(db).firebase_login(payload.id_token)


@router.get("/users/by-email", response_model=AppUserContext)
def get_user_by_email(
    email: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    if not auth_service.is_admin_or_manager(current_user.email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for this resource")

    user = auth_service.user_repository.get_by_email(email.strip().lower())
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role, permissions = auth_service.resolve_role_permissions(user.email)
    profile = user.profile
    return {
        "id": user.id,
        "email": user.email,
        "role": role,
        "permissions": permissions,
        "profile": {
            "first_name": profile.first_name if profile else "",
            "last_name": " ".join(
                item
                for item in [
                    profile.paternal_surname if profile else "",
                    profile.maternal_surname if profile else "",
                ]
                if item
            ).strip(),
            "location_codes": [],
        },
    }

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.orm import Session

from app.core.client_origin import ClientOrigin, get_client_origin
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.scm_auth import (
    AppUserContext,
    FirebaseLoginRequest,
    FirebaseLoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.schemas.scm_user import CurrentUserResponse, UpdateUserRequest
from app.services.svc_auth import AuthService

router = APIRouter(tags=["auth"])


# Adapted from clinic RegisterPatient write flow.
@router.post("/auth/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return AuthService(db).register(payload)


# Adapted from clinic GetPatient read flow.
@router.get("/users/me", response_model=CurrentUserResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AuthService(db).get_profile(current_user.id)


# Adapted member profile update from clinic patient profile mutations.
@router.put("/users/me", response_model=CurrentUserResponse)
def update_me(payload: UpdateUserRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    return AuthService(db).update_profile(current_user.id, data)


@router.post("/auth/firebase-login", response_model=FirebaseLoginResponse)
def firebase_login(
    payload: FirebaseLoginRequest,
    origin: ClientOrigin = Depends(get_client_origin),
    db: Session = Depends(get_db),
):
    return AuthService(db).firebase_login(payload.id_token, origin=origin)


@router.get("/users/by-email", response_model=AppUserContext)
def get_user_by_email(
    email: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    if not auth_service.is_admin_or_manager(current_user):
        raise ForbiddenException("Insufficient permissions for this resource")

    user = auth_service.user_repository.get_by_email(email.strip().lower())
    if user is None:
        raise NotFoundException("User not found")

    role, permissions = auth_service.resolve_role_permissions(user)
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
        },
    }

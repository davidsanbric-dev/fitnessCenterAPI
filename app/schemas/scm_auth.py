from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import EmailStr

from app.schemas import APIModel

if TYPE_CHECKING:
    from app.models import User


class RegisterRequest(APIModel):
    email: EmailStr
    first_name: str
    paternal_surname: str
    maternal_surname: str
    mobile_phone: str
    landline_phone: str | None = None
    birth_date: str | None = None
    address: str | None = None
    # Slug of the TargetCompany the new member belongs to. Optional only when a
    # single company exists (then it is inferred); required otherwise.
    company: str | None = None


class RegisterResponse(APIModel):
    # Provisioning result: identity of the created member. Auth tokens are issued by Firebase.
    id: int
    email: EmailStr
    first_name: str
    paternal_surname: str
    maternal_surname: str

    @classmethod
    def from_model(cls, user: User) -> RegisterResponse:
        profile = user.profile
        return cls(
            id=user.id,
            email=user.email,
            first_name=profile.first_name,
            paternal_surname=profile.paternal_surname,
            maternal_surname=profile.maternal_surname,
        )


class FirebaseLoginRequest(APIModel):
    id_token: str


class AppUserContext(APIModel):
    id: int
    email: EmailStr
    role: str
    permissions: list[str]
    profile: dict[str, str | list[str] | None]

    @classmethod
    def from_user(cls, user: User, role: str, permissions: list[str]) -> AppUserContext:
        # Role/permissions are resolved by the caller (auth service); the profile
        # block collapses the member's name parts into first/last for the clients.
        profile = user.profile
        return cls(
            id=user.id,
            email=user.email,
            role=role,
            permissions=permissions,
            profile={
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
        )


class FirebaseLoginResponse(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: AppUserContext

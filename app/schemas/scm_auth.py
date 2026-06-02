from __future__ import annotations

from pydantic import EmailStr

from app.schemas import APIModel


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


class FirebaseLoginRequest(APIModel):
    id_token: str


class AppUserContext(APIModel):
    id: int
    email: EmailStr
    role: str
    permissions: list[str]
    profile: dict[str, str | list[str] | None]


class FirebaseLoginResponse(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: AppUserContext

from __future__ import annotations

from pydantic import EmailStr, Field

from app.schemas import APIModel


# Adapted from clinic RegisterPatient/GetPatient authless flow -> gym email/password registration flow.
class RegisterRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str
    paternal_surname: str
    maternal_surname: str
    mobile_phone: str
    landline_phone: str | None = None
    birth_date: str | None = None
    address: str | None = None


class LoginRequest(APIModel):
    # Gym auth operation replacing clinic identity lookup command/query flow.
    email: EmailStr
    password: str


class TokenRefreshRequest(APIModel):
    # JWT refresh payload for adapted auth lifecycle.
    refresh_token: str


class TokenResponse(APIModel):
    # Shared token contract for adapted gym authentication endpoints.
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RegisterResponse(TokenResponse):
    # Register response includes adapted member naming fields from clinic patient data.
    id: int
    email: EmailStr
    first_name: str
    paternal_surname: str
    maternal_surname: str


class FirebaseClaimsSyncResponse(APIModel):
    email: EmailStr
    firebase_uid: str
    claims: dict[str, str | int | bool | None]


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

from __future__ import annotations

from enum import Enum

from fastapi import Header, HTTPException, status


class ClientOrigin(str, Enum):
    """Which deployed application a login request originates from.

    Resolved today from the ``X-Client-Platform`` header the clients send. This
    is a product/UX gate rather than a privilege boundary -- the role is always
    resolved from the verified Firebase email, so a spoofed origin cannot
    escalate privilege, only let an account attempt the "wrong" app. A header is
    therefore acceptable here.

    ``get_client_origin`` is the single swap point: replacing it with Firebase
    App Check or per-project ``aud`` verification later strengthens the signal
    without touching the role-gate logic in ``AuthService.firebase_login``.
    """

    MOBILE = "mobile"
    WEB = "web"


_HEADER_VALUES = {origin.value: origin for origin in ClientOrigin}


def get_client_origin(
    x_client_platform: str | None = Header(default=None, alias="X-Client-Platform"),
) -> ClientOrigin:
    origin = _HEADER_VALUES.get((x_client_platform or "").strip().lower())
    if origin is None:
        # Fail closed: an absent or unrecognised client cannot be mapped to an
        # allowed role bucket, so it must not be granted a session.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown client application",
        )
    return origin

from __future__ import annotations

from fastapi import APIRouter

from app.core.media import serve_profile_image

router = APIRouter(prefix="/profile-images", tags=["profile-images"])


# Profile image bytes (trainer photo / member avatar). Unauthenticated so clients
# can render the image directly (Flutter Image.network / <img>); filenames are
# opaque and only handed out inside company-scoped responses. Mirrors the blog
# hero-image media endpoint.
@router.get("/media/{filename}")
def get_profile_media(filename: str):
    return serve_profile_image(filename)

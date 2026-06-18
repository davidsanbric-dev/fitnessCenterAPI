from __future__ import annotations

import base64
import binascii
import logging
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import ALLOWED_IMAGE_TYPES, DATA_URL_RE, settings
from app.core.exceptions import NotFoundException, UnprocessableEntityException
from app.core.tenancy import get_session_company

logger = logging.getLogger("uvicorn.error")

# Image storage on the configured bind volume (``settings.blog_images_path``).
# Cross-cutting infrastructure -- decoding, MIME validation, filesystem I/O, and
# path-traversal safety -- kept out of the domain/service layers. Today it backs
# blog hero images; the storage root is the only blog-specific assumption.


def save_image(db: Session, raw: str, base_dir: str | None = None) -> str:
    # Accept a data URL or raw base64, validate type and encoding, and write the
    # bytes under an opaque, company-scoped filename. Returns the stored filename.
    # ``base_dir`` selects the storage root (defaults to the blog hero-image
    # volume); profile images pass ``settings.profile_images_path``.
    mime, payload = _parse_data_url(raw)
    extension = ALLOWED_IMAGE_TYPES.get(mime)
    if extension is None:
        raise UnprocessableEntityException("Unsupported image type. Allowed: PNG, JPEG, WEBP, GIF.")
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise UnprocessableEntityException("Invalid image encoding")

    company_id = get_session_company(db) or 0
    directory = Path(base_dir or settings.blog_images_path)
    directory.mkdir(parents=True, exist_ok=True)
    stored = directory / f"{company_id}_{uuid4().hex}{extension}"
    stored.write_bytes(data)

    # Optimise server disk usage by transcoding raster uploads to WebP at q80
    # (``cwebp -q 80 in.png -o out.webp``). WebP inputs are already optimal, and
    # a missing encoder or a conversion failure falls back to the stored bytes.
    if extension != ".webp":
        converted = _convert_to_webp(stored)
        if converted is not None:
            stored = converted
    return stored.name


def serve_image(filename: str, base_dir: str | None = None) -> FileResponse:
    base = Path(base_dir or settings.blog_images_path).resolve()
    # Reject any path traversal: only a bare filename inside the base dir.
    target = (base / Path(filename).name).resolve()
    if base not in target.parents or not target.is_file():
        raise NotFoundException("Image not found")
    return FileResponse(target)


def delete_image(filename: str, base_dir: str | None = None) -> None:
    # Best-effort: a failed unlink must never break the calling mutation.
    try:
        target = Path(base_dir or settings.blog_images_path).resolve() / Path(filename).name
        if target.is_file():
            target.unlink()
    except OSError:
        logger.warning("Could not delete image %s", filename, exc_info=True)


# ---- Profile images (trainer photo / member avatar) ---------------------------
# Thin wrappers binding the generic helpers above to the profile-image volume,
# plus the stored-filename -> served-URL projection mirrored on response schemas.

_PROFILE_MEDIA_PREFIX = "/profile-images/media/"


def save_profile_image(db: Session, raw: str) -> str:
    return save_image(db, raw, base_dir=settings.profile_images_path)


def serve_profile_image(filename: str) -> FileResponse:
    return serve_image(filename, base_dir=settings.profile_images_path)


def delete_profile_image(filename: str | None) -> None:
    # Only reclaim bare opaque filenames we own; legacy/seeded absolute paths
    # (``/images/trainers/...``) and external URLs are left untouched.
    if filename and not filename.startswith(("/", "http://", "https://")):
        delete_image(filename, base_dir=settings.profile_images_path)


def profile_image_url(stored: str | None) -> str | None:
    # Project a stored profile-image value to a client-fetchable URL. Bare
    # filenames (uploads + the seed) become a media URL; legacy absolute paths
    # and full URLs pass through unchanged so old rows never 404 differently.
    if not stored:
        return None
    if stored.startswith(("/", "http://", "https://")):
        return stored
    return f"{_PROFILE_MEDIA_PREFIX}{stored}"


def _convert_to_webp(source: Path) -> Path | None:
    # Run cwebp to produce a sibling ``.webp`` and drop the original on success.
    # Returns None (keeping the original) when the tool is absent or fails, so an
    # upload is never lost to a transcoding problem.
    cwebp = shutil.which("cwebp")
    if cwebp is None:
        logger.warning("cwebp not found; storing %s without WebP conversion", source.name)
        return None
    target = source.with_suffix(".webp")
    try:
        subprocess.run(
            [cwebp, "-q", "80", str(source), "-o", str(target)],
            check=True,
            capture_output=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        logger.warning("WebP conversion failed for %s; keeping original", source.name, exc_info=True)
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    source.unlink(missing_ok=True)
    return target


def _parse_data_url(raw: str) -> tuple[str, str]:
    match = DATA_URL_RE.match(raw.strip())
    if match:
        return match.group("mime").lower(), match.group("payload")
    # Raw base64 without a data-URL prefix: assume PNG.
    return "image/png", raw.strip()

from __future__ import annotations

import base64
import binascii
import logging
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


def save_image(db: Session, raw: str) -> str:
    # Accept a data URL or raw base64, validate type and encoding, and write the
    # bytes under an opaque, company-scoped filename. Returns the stored filename.
    mime, payload = _parse_data_url(raw)
    extension = ALLOWED_IMAGE_TYPES.get(mime)
    if extension is None:
        raise UnprocessableEntityException("Unsupported image type. Allowed: PNG, JPEG, WEBP, GIF.")
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise UnprocessableEntityException("Invalid image encoding")

    company_id = get_session_company(db) or 0
    filename = f"{company_id}_{uuid4().hex}{extension}"
    directory = Path(settings.blog_images_path)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_bytes(data)
    return filename


def serve_image(filename: str) -> FileResponse:
    base = Path(settings.blog_images_path).resolve()
    # Reject any path traversal: only a bare filename inside the base dir.
    target = (base / Path(filename).name).resolve()
    if base not in target.parents or not target.is_file():
        raise NotFoundException("Image not found")
    return FileResponse(target)


def delete_image(filename: str) -> None:
    # Best-effort: a failed unlink must never break the calling mutation.
    try:
        target = Path(settings.blog_images_path).resolve() / Path(filename).name
        if target.is_file():
            target.unlink()
    except OSError:
        logger.warning("Could not delete image %s", filename, exc_info=True)


def _parse_data_url(raw: str) -> tuple[str, str]:
    match = DATA_URL_RE.match(raw.strip())
    if match:
        return match.group("mime").lower(), match.group("payload")
    # Raw base64 without a data-URL prefix: assume PNG.
    return "image/png", raw.strip()

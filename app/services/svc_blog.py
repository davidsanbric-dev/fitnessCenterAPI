from __future__ import annotations

import base64
import binascii
import logging
import re
from pathlib import Path
from uuid import uuid4

from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundException, UnprocessableEntityException
from app.core.push import send_push_to_tokens
from app.core.tenancy import get_session_company
from app.models import Blog
from app.repositories.rps_blog import BlogRepository
from app.repositories.rps_notification import NotificationRepository
from app.schemas.scm_blog import BlogUpsertRequest
from app.services.svc_common import get_or_404

logger = logging.getLogger("uvicorn.error")

# Allowed image content types -> file extension written to the bind volume.
_ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_DATA_URL_RE = re.compile(r"^data:(?P<mime>[\w/+.-]+);base64,(?P<payload>.+)$", re.DOTALL)


class BlogService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = BlogRepository(db)

    # ---- reads -----------------------------------------------------------
    def list_blogs(self, search: str | None, page: int, page_size: int) -> dict:
        blogs, total = self.repository.list_blogs(search, page, page_size)
        return {
            "items": [self._serialize(blog) for blog in blogs],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_blog(self, blog_id: int) -> dict:
        blog = get_or_404(self.repository.get_blog(blog_id), "Blog entry not found")
        return self._serialize(blog)

    # ---- writes ----------------------------------------------------------
    def create_blog(self, payload: BlogUpsertRequest) -> dict:
        title = (payload.title or "").strip()
        if not title:
            raise UnprocessableEntityException("Title is required")
        if not payload.hero_image:
            raise UnprocessableEntityException("Hero image is required")

        hero_image_path = self._save_image(payload.hero_image)
        blog = self.repository.create_blog(
            Blog(title=title, text=payload.text or "", hero_image_path=hero_image_path)
        )
        self._notify_new_blog(blog)
        return self._serialize(blog)

    def update_blog(self, blog_id: int, payload: BlogUpsertRequest) -> dict:
        blog = get_or_404(self.repository.get_blog(blog_id), "Blog entry not found")

        title = (payload.title or "").strip()
        if not title:
            raise UnprocessableEntityException("Title is required")

        updates: dict = {"title": title, "text": payload.text or ""}
        # Only replace the image when a new one is supplied; otherwise keep it.
        if payload.hero_image:
            new_path = self._save_image(payload.hero_image)
            old_path = blog.hero_image_path
            updates["hero_image_path"] = new_path
            if old_path and old_path != new_path:
                self._delete_image_file(old_path)

        updated = self.repository.update_blog(blog, updates)
        return self._serialize(updated)

    def delete_blog(self, blog_id: int) -> dict:
        blog = get_or_404(self.repository.get_blog(blog_id), "Blog entry not found")
        image_path = blog.hero_image_path
        self.repository.delete_blog(blog)
        if image_path:
            self._delete_image_file(image_path)
        return {"message": "Blog entry deleted"}

    # ---- media serving (unauthenticated; opaque uuid filenames) ----------
    @staticmethod
    def serve_media(filename: str) -> FileResponse:
        base = Path(settings.blog_images_path).resolve()
        # Reject any path traversal: only a bare filename inside the base dir.
        target = (base / Path(filename).name).resolve()
        if base not in target.parents or not target.is_file():
            raise NotFoundException("Image not found")
        return FileResponse(target)

    # ---- notifications ---------------------------------------------------
    def _notify_new_blog(self, blog: Blog) -> None:
        # Push a "new blog" FCM message to every device registered for this
        # company (device tokens are tenant-scoped). Best-effort: a push failure
        # must never break blog creation. Stale tokens are pruned.
        try:
            notifications = NotificationRepository(self.db)
            tokens = [device.token for device in notifications.list_device_tokens()]
            if not tokens:
                return
            invalid = send_push_to_tokens(
                tokens,
                title="New post",
                body=blog.title,
                data={"type": "blog_created", "blog_id": blog.id},
            )
            if invalid:
                notifications.prune_tokens(invalid)
        except Exception:
            logger.warning("Failed to dispatch blog push notification", exc_info=True)

    # ---- helpers ---------------------------------------------------------
    def _serialize(self, blog: Blog) -> dict:
        return {
            "id": blog.id,
            "title": blog.title,
            "text": blog.text or "",
            "hero_image_url": f"/blog/media/{blog.hero_image_path}" if blog.hero_image_path else None,
            "created_at": blog.created_at,
            "updated_at": blog.updated_at,
        }

    def _save_image(self, raw: str) -> str:
        mime, payload = self._parse_image(raw)
        extension = _ALLOWED_IMAGE_TYPES.get(mime)
        if extension is None:
            raise UnprocessableEntityException("Unsupported image type. Allowed: PNG, JPEG, WEBP, GIF.")
        try:
            data = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError):
            raise UnprocessableEntityException("Invalid image encoding")

        company_id = get_session_company(self.db) or 0
        filename = f"{company_id}_{uuid4().hex}{extension}"
        directory = Path(settings.blog_images_path)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / filename).write_bytes(data)
        return filename

    @staticmethod
    def _parse_image(raw: str) -> tuple[str, str]:
        match = _DATA_URL_RE.match(raw.strip())
        if match:
            return match.group("mime").lower(), match.group("payload")
        # Raw base64 without a data-URL prefix: assume PNG.
        return "image/png", raw.strip()

    @staticmethod
    def _delete_image_file(filename: str) -> None:
        try:
            target = (Path(settings.blog_images_path).resolve() / Path(filename).name)
            if target.is_file():
                target.unlink()
        except OSError:
            logger.warning("Could not delete blog image %s", filename, exc_info=True)

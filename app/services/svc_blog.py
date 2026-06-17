from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.media import delete_image, save_image
from app.models import Blog
from app.repositories.rps_blog import BlogRepository
from app.schemas import PaginatedResponse
from app.schemas.scm_blog import BlogCreateRequest, BlogResponse, BlogUpdateRequest
from app.services.svc_notification import NotificationService
from app.services.validators import BlogGuards


class BlogService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = BlogRepository(db)
        self.guards = BlogGuards(self.repository)

    def list_blogs(self, search: str | None, page: int, page_size: int) -> PaginatedResponse[BlogResponse]:
        blogs, total = self.repository.list_blogs(search, page, page_size)
        return PaginatedResponse[BlogResponse].build(
            items=[BlogResponse.from_model(blog) for blog in blogs],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_blog(self, blog_id: int) -> BlogResponse:
        blog = self.guards.require_existing(blog_id)
        return BlogResponse.from_model(blog)

    def create_blog(self, payload: BlogCreateRequest) -> BlogResponse:
        # Title is required/stripped and hero_image required by BlogCreateRequest.
        hero_image_path = save_image(self.db, payload.hero_image)
        blog = self.repository.create_blog(
            Blog(title=payload.title, text=payload.text or "", hero_image_path=hero_image_path)
        )
        self._notify_new_blog(blog)
        return BlogResponse.from_model(blog)

    def update_blog(self, blog_id: int, payload: BlogUpdateRequest) -> BlogResponse:
        blog = self.guards.require_existing(blog_id)

        updates: dict = {"title": payload.title, "text": payload.text or ""}
        if payload.hero_image:
            new_path = save_image(self.db, payload.hero_image)
            old_path = blog.hero_image_path
            updates["hero_image_path"] = new_path
            if old_path and old_path != new_path:
                delete_image(old_path)

        updated = self.repository.update_blog(blog, updates)
        return BlogResponse.from_model(updated)

    def delete_blog(self, blog_id: int) -> dict:
        blog = self.guards.require_existing(blog_id)
        image_path = blog.hero_image_path
        # Seeded demo blogs reuse the same hero image across several companies, so
        # only reclaim the file when no other blog still references it; otherwise
        # deleting one entry would break the others' images.
        shared = bool(image_path) and self.repository.count_blogs_sharing_image(image_path, blog_id) > 0
        self.repository.delete_blog(blog)
        if image_path and not shared:
            delete_image(image_path)
        return {"message": "Blog entry deleted"}

    def _notify_new_blog(self, blog: Blog) -> None:
        NotificationService(self.db).broadcast_push(
            title="New post",
            body=blog.title,
            data={"type": "blog_created", "blog_id": blog.id},
        )

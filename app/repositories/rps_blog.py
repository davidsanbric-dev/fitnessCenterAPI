from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Blog


# Repository for company-scoped blog entries. Reads are auto-filtered to the
# caller's company and writes auto-stamped with it (see app.core.tenancy).
class BlogRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_blogs(self, search: str | None = None, page: int = 1, page_size: int = 20) -> tuple[list[Blog], int]:
        statement = select(Blog)
        count_statement = select(func.count()).select_from(Blog)
        if search:
            pattern = f"%{search}%"
            condition = or_(Blog.title.ilike(pattern), Blog.text.ilike(pattern))
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)
        total = int(self.db.scalar(count_statement) or 0)
        items = self.db.scalars(
            statement.order_by(Blog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return list(items), total

    def get_blog(self, blog_id: int) -> Blog | None:
        return self.db.scalar(select(Blog).where(Blog.id == blog_id))

    def create_blog(self, blog: Blog) -> Blog:
        self.db.add(blog)
        self.db.commit()
        self.db.refresh(blog)
        return blog

    def update_blog(self, blog: Blog, payload: dict) -> Blog:
        for field, value in payload.items():
            setattr(blog, field, value)
        self.db.commit()
        self.db.refresh(blog)
        return blog

    def delete_blog(self, blog: Blog) -> None:
        self.db.delete(blog)
        self.db.commit()

    def count_blogs_sharing_image(self, image_path: str, exclude_blog_id: int) -> int:
        # Cross-company count of *other* blogs pointing at the same stored image.
        # Selecting from the Core table (not the mapped class) sidesteps the
        # tenant loader criteria, so seeded hero images shared across companies
        # are correctly seen as still-referenced. Used to decide whether deleting
        # a blog may also reclaim its image file.
        table = Blog.__table__
        statement = (
            select(func.count())
            .select_from(table)
            .where(table.c.hero_image_path == image_path, table.c.id != exclude_blog_id)
        )
        return int(self.db.scalar(statement) or 0)

from __future__ import annotations

from datetime import datetime
from typing import Annotated, TYPE_CHECKING

from pydantic import Field, StringConstraints

from app.schemas import APIModel

if TYPE_CHECKING:
    from app.models import Blog


# Title is required and non-blank; surrounding whitespace is stripped so a value
# of "   " is rejected (min_length applies after the strip) and the stored title
# carries no padding.
BlogTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


# Company-scoped blog entry projection. ``hero_image_url`` is a path relative to
# the API v1 base (the same base clients already use for endpoints), e.g.
# "/blog/media/3_ab12.png"; clients prepend their configured API base URL.
class BlogResponse(APIModel):
    id: int
    title: str
    text: str
    hero_image_url: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, blog: Blog) -> BlogResponse:
        # The stored image is an opaque filename; expose it as a media URL.
        return cls(
            id=blog.id,
            title=blog.title,
            text=blog.text or "",
            hero_image_url=f"/blog/media/{blog.hero_image_path}" if blog.hero_image_path else None,
            created_at=blog.created_at,
            updated_at=blog.updated_at,
        )


class BlogWriteBase(APIModel):
    title: BlogTitle
    text: str = ""


class BlogCreateRequest(BlogWriteBase):
    # Hero image as a data URL ("data:image/png;base64,....") or raw base64.
    # Required on create.
    hero_image: str = Field(min_length=1)


class BlogUpdateRequest(BlogWriteBase):
    # Omit/null to keep the existing image; otherwise replaces it.
    hero_image: str | None = None

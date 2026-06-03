from __future__ import annotations

from datetime import datetime

from app.schemas import APIModel


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


class BlogUpsertRequest(APIModel):
    title: str
    text: str = ""
    # Hero image as a data URL ("data:image/png;base64,....") or raw base64.
    # Required on create; on update, omit/null to keep the existing image.
    hero_image: str | None = None

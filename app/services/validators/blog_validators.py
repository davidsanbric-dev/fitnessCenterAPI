from __future__ import annotations

from app.models import Blog
from app.repositories.rps_blog import BlogRepository
from app.services.svc_common import get_or_404


class BlogGuards:
    """Preconditions for blog use cases.

    Repository-backed existence checks shared by the read/update/delete paths.
    Constructed with the same repository the service uses, so guards and service
    share one persistence context.
    """

    def __init__(self, repository: BlogRepository):
        self._repo = repository

    def require_existing(self, blog_id: int) -> Blog:
        # Single existence guard for a blog entry, shared by get/update/delete so
        # the "not found" message lives in one place.
        return get_or_404(self._repo.get_blog(blog_id), "Blog entry not found")

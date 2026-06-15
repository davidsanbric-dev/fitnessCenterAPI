from __future__ import annotations

# Shared schema primitives live in scm_common (parallel to svc_common); re-exported
# here so the established ``from app.schemas import APIModel`` imports keep working.
from app.schemas.scm_common import APIModel, MessageResponse, PaginatedResponse

__all__ = ["APIModel", "MessageResponse", "PaginatedResponse"]

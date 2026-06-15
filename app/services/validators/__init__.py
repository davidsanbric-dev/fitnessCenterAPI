"""Application-layer validators ("guards").

Preconditions for a use case -- existence, ownership, uniqueness, availability,
eligibility -- that need to consult persistence or an entity's loaded
relationships, and therefore cannot live in the pure ``app.domain`` layer. Each
guard class wraps the repository for one aggregate and may delegate the rule
itself to a domain policy; services compose it. Pure, storage-independent
invariants belong in ``app.domain`` instead.
"""

from __future__ import annotations

from app.services.validators.auth_validators import AuthGuards
from app.services.validators.blog_validators import BlogGuards
from app.services.validators.booking_validators import BookingGuards

__all__ = ["AuthGuards", "BlogGuards", "BookingGuards"]

from __future__ import annotations

from datetime import date, datetime, time
from typing import TypeVar

from app.core.exceptions import NotFoundException

T = TypeVar("T")


def get_or_404(instance: T | None, detail: str) -> T:
    """Return ``instance`` or raise a 404 with ``detail`` when it is ``None``.

    Collapses the repeated "fetch then null-check" guard used across services
    into one typed expression (the return type narrows away the ``None``).
    """
    if instance is None:
        raise NotFoundException(detail)
    return instance


def parse_datetime_parts(date_value: str, time_value: str) -> datetime:
    return datetime.combine(date.fromisoformat(date_value), time.fromisoformat(time_value))



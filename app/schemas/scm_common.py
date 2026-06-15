from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(APIModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @classmethod
    def build(cls, items: list[T], total: int, page: int, page_size: int) -> PaginatedResponse[T]:
        # One envelope builder for every paginated list endpoint; callers map their
        # rows to DTOs and pass the parametrized class (PaginatedResponse[Dto]).
        return cls(items=items, total=total, page=page, page_size=page_size)


class MessageResponse(APIModel):
    message: str

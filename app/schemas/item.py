"""
Pydantic schemas for Item resource.
"""

from __future__ import annotations

from pydantic import BaseModel


class ItemCreate(BaseModel):
    title: str
    description: str | None = None
    price: float = 0.0
    is_active: bool = True


class ItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    is_active: bool | None = None


class ItemResponse(BaseModel):
    id: int
    title: str
    description: str | None
    price: float
    is_active: bool
    owner_id: int | None

    model_config = {"from_attributes": True}

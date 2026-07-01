"""
SQLAlchemy ORM model for the Item entity.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Item(Base):
    __tablename__ = "items"

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    owner: Mapped["User | None"] = relationship("User", back_populates="items")  # noqa: F821

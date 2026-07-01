"""
SQLAlchemy declarative base shared by all ORM models.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, MappedColumn, mapped_column
from sqlalchemy import Integer


class Base(DeclarativeBase):
    """Project-wide SQLAlchemy base class."""

    # Every table gets an auto-incremented integer PK by default.
    id: MappedColumn[int] = mapped_column(Integer, primary_key=True, index=True)

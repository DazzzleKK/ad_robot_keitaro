from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.dictionaries.dto import DictionaryType


class DictionaryItemModel(Base):
    __tablename__ = "dictionary_item"
    __table_args__ = (UniqueConstraint("type", "keitaro_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[DictionaryType] = mapped_column(
        sa.Enum(
            DictionaryType,
            name="dictionary_type",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    keitaro_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.text("CURRENT_TIMESTAMP"),
    )

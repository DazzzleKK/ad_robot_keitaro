from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.campaigns.enums import StreamKind
from src.database import Base


class CampaignModel(Base):
    __tablename__ = "campaign"
    __table_args__ = (UniqueConstraint("keitaro_campaign_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    keitaro_campaign_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain_id: Mapped[int] = mapped_column(Integer, nullable=False)
    group_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
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

    streams: Mapped[list[CampaignStreamModel]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
    )


class CampaignStreamModel(Base):
    __tablename__ = "campaign_stream"
    __table_args__ = (
        UniqueConstraint("campaign_id", "keitaro_stream_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaign.id", ondelete="CASCADE"),
        nullable=False,
    )
    keitaro_stream_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[StreamKind] = mapped_column(
        sa.Enum(
            StreamKind,
            name="stream_kind",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
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

    campaign: Mapped[CampaignModel] = relationship(back_populates="streams")
    offers: Mapped[list[StreamOfferModel]] = relationship(
        back_populates="stream",
        cascade="all, delete-orphan",
    )


class StreamOfferModel(Base):
    __tablename__ = "stream_offer"
    __table_args__ = (UniqueConstraint("stream_id", "keitaro_offer_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stream_id: Mapped[int] = mapped_column(
        ForeignKey("campaign_stream.id", ondelete="CASCADE"),
        nullable=False,
    )
    keitaro_offer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=sa.true(),
    )
    pinned_weight: Mapped[int | None] = mapped_column(Integer, nullable=True)
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

    stream: Mapped[CampaignStreamModel] = relationship(back_populates="offers")

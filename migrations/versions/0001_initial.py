"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-06-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaign",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("keitaro_campaign_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("keitaro_campaign_id"),
    )
    op.create_index(
        "ix_campaign_keitaro_campaign_id",
        "campaign",
        ["keitaro_campaign_id"],
        unique=False,
    )

    op.create_table(
        "campaign_stream",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "campaign_id",
            sa.Integer(),
            sa.ForeignKey("campaign.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("keitaro_stream_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "geo_redirect",
                "offers",
                name="stream_kind",
                native_enum=False,
                validate_strings=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("campaign_id", "keitaro_stream_id"),
    )

    op.create_table(
        "stream_offer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "stream_id",
            sa.Integer(),
            sa.ForeignKey("campaign_stream.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("keitaro_offer_id", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("pinned_weight", sa.Integer(), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("stream_id", "keitaro_offer_id"),
    )

    op.create_table(
        "dictionary_item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "type",
            sa.Enum(
                "domains",
                "groups",
                "sources",
                "offers",
                name="dictionary_type",
                native_enum=False,
                validate_strings=True,
            ),
            nullable=False,
        ),
        sa.Column("keitaro_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("type", "keitaro_id"),
    )


def downgrade() -> None:
    op.drop_table("dictionary_item")
    op.drop_table("stream_offer")
    op.drop_table("campaign_stream")
    op.drop_index("ix_campaign_keitaro_campaign_id", table_name="campaign")
    op.drop_table("campaign")

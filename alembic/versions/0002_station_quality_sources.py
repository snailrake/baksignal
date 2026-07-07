"""Add station quality fields and raw source links.

Revision ID: 0002_station_quality_sources
Revises: 0001_initial
Create Date: 2026-07-08 02:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_station_quality_sources"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    verification_status = sa.Enum(
        "active",
        "needs_review",
        "hidden",
        "closed",
        name="stationverificationstatus",
    )
    verification_status.create(op.get_bind(), checkfirst=True)

    with op.batch_alter_table("stations") as batch_op:
        batch_op.add_column(
            sa.Column(
                "verification_status",
                verification_status,
                nullable=False,
                server_default="active",
            )
        )
        batch_op.add_column(sa.Column("quality_score", sa.Integer(), nullable=False, server_default="50"))
        batch_op.add_column(sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_stations_verification_status", ["verification_status"])

    op.create_table(
        "station_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("external_id", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("brand", sa.String(length=80), nullable=True),
        sa.Column("address", sa.String(length=240), nullable=False),
        sa.Column("lat", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("lon", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("is_active_signal", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_station_sources_source_external"),
    )
    op.create_index(op.f("ix_station_sources_brand"), "station_sources", ["brand"])
    op.create_index(op.f("ix_station_sources_is_active_signal"), "station_sources", ["is_active_signal"])
    op.create_index(op.f("ix_station_sources_source"), "station_sources", ["source"])
    op.create_index(op.f("ix_station_sources_station_id"), "station_sources", ["station_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_station_sources_station_id"), table_name="station_sources")
    op.drop_index(op.f("ix_station_sources_source"), table_name="station_sources")
    op.drop_index(op.f("ix_station_sources_is_active_signal"), table_name="station_sources")
    op.drop_index(op.f("ix_station_sources_brand"), table_name="station_sources")
    op.drop_table("station_sources")

    with op.batch_alter_table("stations") as batch_op:
        batch_op.drop_index("ix_stations_verification_status")
        batch_op.drop_column("closed_at")
        batch_op.drop_column("last_verified_at")
        batch_op.drop_column("quality_score")
        batch_op.drop_column("verification_status")

    sa.Enum(name="stationverificationstatus").drop(op.get_bind(), checkfirst=True)

"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    fuel_type = sa.Enum("ai92", "ai95", "diesel", name="fueltype")
    availability = sa.Enum("yes", "no", "unknown", name="availability")
    queue_level = sa.Enum("none", "small", "medium", "large", "unknown", name="queuelevel")
    source_type = sa.Enum("user", "admin", "public_news", "imported", name="sourcetype")

    op.create_table(
        "stations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("brand", sa.String(length=80), nullable=True),
        sa.Column("address", sa.String(length=240), nullable=False),
        sa.Column("district", sa.String(length=80), nullable=True),
        sa.Column("lat", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("lon", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_station_source_external"),
    )
    op.create_index(op.f("ix_stations_brand"), "stations", ["brand"])
    op.create_index(op.f("ix_stations_district"), "stations", ["district"])

    op.create_table(
        "fuel_observations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("fuel_type", fuel_type, nullable=False),
        sa.Column("availability", availability, nullable=False),
        sa.Column("queue_level", queue_level, nullable=False),
        sa.Column("limit_liters", sa.Integer(), nullable=True),
        sa.Column("price", sa.Numeric(precision=7, scale=2), nullable=True),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("telegram_user_id", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fuel_observations_availability"), "fuel_observations", ["availability"])
    op.create_index(op.f("ix_fuel_observations_created_at"), "fuel_observations", ["created_at"])
    op.create_index(op.f("ix_fuel_observations_expires_at"), "fuel_observations", ["expires_at"])
    op.create_index(op.f("ix_fuel_observations_fuel_type"), "fuel_observations", ["fuel_type"])
    op.create_index(op.f("ix_fuel_observations_source_type"), "fuel_observations", ["source_type"])
    op.create_index(op.f("ix_fuel_observations_station_id"), "fuel_observations", ["station_id"])
    op.create_index(
        op.f("ix_fuel_observations_telegram_user_id"),
        "fuel_observations",
        ["telegram_user_id"],
    )

    op.create_table(
        "station_fuel_statuses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("fuel_type", fuel_type, nullable=False),
        sa.Column("availability", availability, nullable=False),
        sa.Column("queue_level", queue_level, nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("observation_id", sa.Integer(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["observation_id"], ["fuel_observations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["station_id"], ["stations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("station_id", "fuel_type", name="uq_status_station_fuel"),
    )
    op.create_index(op.f("ix_station_fuel_statuses_availability"), "station_fuel_statuses", ["availability"])
    op.create_index(op.f("ix_station_fuel_statuses_expires_at"), "station_fuel_statuses", ["expires_at"])
    op.create_index(op.f("ix_station_fuel_statuses_fuel_type"), "station_fuel_statuses", ["fuel_type"])
    op.create_index(op.f("ix_station_fuel_statuses_observed_at"), "station_fuel_statuses", ["observed_at"])
    op.create_index(op.f("ix_station_fuel_statuses_source_type"), "station_fuel_statuses", ["source_type"])
    op.create_index(op.f("ix_station_fuel_statuses_station_id"), "station_fuel_statuses", ["station_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.Integer(), nullable=False),
        sa.Column("fuel_type", fuel_type, nullable=False),
        sa.Column("district", sa.String(length=80), nullable=True),
        sa.Column("center_lat", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("center_lon", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("radius_m", sa.Integer(), nullable=True),
        sa.Column("notify_queue_max", queue_level, nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_user_id", "fuel_type", "district", name="uq_subscription_user_scope"),
    )
    op.create_index(op.f("ix_subscriptions_active"), "subscriptions", ["active"])
    op.create_index(op.f("ix_subscriptions_district"), "subscriptions", ["district"])
    op.create_index(op.f("ix_subscriptions_fuel_type"), "subscriptions", ["fuel_type"])
    op.create_index(op.f("ix_subscriptions_telegram_user_id"), "subscriptions", ["telegram_user_id"])


def downgrade() -> None:
    op.drop_table("subscriptions")
    op.drop_table("station_fuel_statuses")
    op.drop_table("fuel_observations")
    op.drop_table("stations")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS fueltype")
        op.execute("DROP TYPE IF EXISTS availability")
        op.execute("DROP TYPE IF EXISTS queuelevel")
        op.execute("DROP TYPE IF EXISTS sourcetype")

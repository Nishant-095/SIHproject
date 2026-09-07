"""Create Phase 1-3 collection and provenance tables.

Revision ID: 20260905_0001
Revises: None
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260905_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def enum_values(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def upgrade() -> None:
    uuid_type = sa.Uuid()
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    op.create_table(
        "sources",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "source_type",
            enum_values("AIRLINE_DIRECT", "OTA", "PUBLIC_DATA", "FIXTURE", name="source_type"),
            nullable=False,
        ),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("collection_method", sa.String(length=40), nullable=False),
        sa.Column(
            "review_status",
            enum_values(
                "PENDING_REVIEW",
                "APPROVED",
                "RESTRICTED",
                "BLOCKED",
                "PARSER_CHANGED",
                "DISABLED",
                name="source_review_status",
            ),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=True),
        sa.Column("max_concurrency", sa.Integer(), nullable=False),
        sa.Column("parser_version", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_sources_code"), "sources", ["code"], unique=True)

    op.create_table(
        "routes",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("origin_iata", sa.String(length=3), nullable=False),
        sa.Column("destination_iata", sa.String(length=3), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("selection_basis", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("origin_iata <> destination_iata", name="ck_routes_distinct_airports"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("origin_iata", "destination_iata", name="uq_routes_direction"),
    )

    op.create_table(
        "collection_runs",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("methodological_date", sa.Date(), nullable=False),
        sa.Column("scheduled_for_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            enum_values("PLANNED", "RUNNING", "COMPLETED", "PARTIAL", "FAILED", name="run_status"),
            nullable=False,
        ),
        sa.Column(
            "trigger_type",
            enum_values("SCHEDULED", "MANUAL", "BACKFILL", "TEST", name="run_trigger"),
            nullable=False,
        ),
        sa.Column(
            "data_class",
            enum_values("LIVE", "HISTORICAL", "SYNTHETIC", "RECORDED_DEMO", name="data_class"),
            nullable=False,
        ),
        sa.Column("planned_jobs", sa.Integer(), nullable=False),
        sa.Column("successful_jobs", sa.Integer(), nullable=False),
        sa.Column("failed_jobs", sa.Integer(), nullable=False),
        sa.Column("valid_observations", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("failed_jobs >= 0", name="ck_runs_failed_jobs_nonnegative"),
        sa.CheckConstraint("planned_jobs >= 0", name="ck_runs_planned_jobs_nonnegative"),
        sa.CheckConstraint("successful_jobs >= 0", name="ck_runs_successful_jobs_nonnegative"),
        sa.CheckConstraint(
            "valid_observations >= 0", name="ck_runs_valid_observations_nonnegative"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "methodological_date",
            "trigger_type",
            "data_class",
            name="uq_runs_method_date_trigger_class",
        ),
    )

    op.create_table(
        "collection_jobs",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("collection_run_id", uuid_type, nullable=False),
        sa.Column("source_id", uuid_type, nullable=False),
        sa.Column("route_id", uuid_type, nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("advance_days", sa.Integer(), nullable=False),
        sa.Column(
            "advance_window",
            enum_values("T1", "T7", "T15", "T30", "T45", "OTHER", name="advance_window"),
            nullable=False,
        ),
        sa.Column(
            "status",
            enum_values("PLANNED", "RUNNING", "SUCCEEDED", "FAILED", "SKIPPED", name="job_status"),
            nullable=False,
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "failure_code",
            enum_values(
                "SOURCE_UNAVAILABLE",
                "RATE_LIMITED",
                "ROBOTS_DISALLOWED",
                "TERMS_RESTRICTED",
                "CAPTCHA_BLOCKED",
                "AUTHENTICATION_FAILED",
                "PARSER_CHANGED",
                "NO_RESULTS",
                "NETWORK_TIMEOUT",
                "INVALID_RESPONSE",
                "UNKNOWN_ERROR",
                name="failure_code",
            ),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("advance_days >= 0", name="ck_jobs_advance_days_nonnegative"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_jobs_attempt_count_nonnegative"),
        sa.ForeignKeyConstraint(["collection_run_id"], ["collection_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        op.f("ix_collection_jobs_collection_run_id"), "collection_jobs", ["collection_run_id"]
    )
    op.create_index(op.f("ix_collection_jobs_route_id"), "collection_jobs", ["route_id"])
    op.create_index(op.f("ix_collection_jobs_source_id"), "collection_jobs", ["source_id"])
    op.create_index(op.f("ix_collection_jobs_travel_date"), "collection_jobs", ["travel_date"])
    op.create_index(
        op.f("ix_collection_jobs_advance_window"), "collection_jobs", ["advance_window"]
    )

    op.create_table(
        "raw_quotes",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("collection_job_id", uuid_type, nullable=False),
        sa.Column("source_id", uuid_type, nullable=False),
        sa.Column(
            "data_class",
            enum_values("LIVE", "HISTORICAL", "SYNTHETIC", "RECORDED_DEMO", name="raw_data_class"),
            nullable=False,
        ),
        sa.Column("observed_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("query_origin", sa.String(length=8), nullable=False),
        sa.Column("query_destination", sa.String(length=8), nullable=False),
        sa.Column("query_travel_date", sa.Date(), nullable=False),
        sa.Column("raw_airline_name", sa.Text(), nullable=True),
        sa.Column("raw_flight_number", sa.Text(), nullable=True),
        sa.Column("raw_departure", sa.Text(), nullable=True),
        sa.Column("raw_arrival", sa.Text(), nullable=True),
        sa.Column("raw_fare_text", sa.Text(), nullable=True),
        sa.Column("raw_currency", sa.String(length=3), nullable=True),
        sa.Column("raw_base_fare", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("raw_tax_text", sa.Text(), nullable=True),
        sa.Column("raw_total_fare", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("raw_payload", json_type, nullable=False),
        sa.Column("parser_version", sa.String(length=40), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["collection_job_id"], ["collection_jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_job_id", "content_hash", name="uq_raw_job_content"),
    )
    op.create_index(op.f("ix_raw_quotes_collection_job_id"), "raw_quotes", ["collection_job_id"])
    op.create_index(op.f("ix_raw_quotes_content_hash"), "raw_quotes", ["content_hash"])
    op.create_index(op.f("ix_raw_quotes_observed_at_utc"), "raw_quotes", ["observed_at_utc"])
    op.create_index(op.f("ix_raw_quotes_source_id"), "raw_quotes", ["source_id"])

    op.create_table(
        "fare_observations",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("raw_quote_id", uuid_type, nullable=False),
        sa.Column("observed_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("methodological_date", sa.Date(), nullable=False),
        sa.Column("origin_iata", sa.String(length=3), nullable=False),
        sa.Column("destination_iata", sa.String(length=3), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("advance_days", sa.Integer(), nullable=False),
        sa.Column(
            "advance_window",
            enum_values(
                "T1", "T7", "T15", "T30", "T45", "OTHER", name="observation_advance_window"
            ),
            nullable=False,
        ),
        sa.Column("carrier_code", sa.String(length=4), nullable=True),
        sa.Column("carrier_name", sa.String(length=120), nullable=True),
        sa.Column("flight_number", sa.String(length=16), nullable=True),
        sa.Column("departure_time_local", sa.Time(), nullable=True),
        sa.Column("arrival_time_local", sa.Time(), nullable=True),
        sa.Column("is_nonstop", sa.Boolean(), nullable=True),
        sa.Column("cabin_class", sa.String(length=40), nullable=True),
        sa.Column("fare_class", sa.String(length=80), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("base_fare", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("taxes", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("udf", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("convenience_fee", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("other_fees", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("total_fare", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "availability",
            enum_values(
                "AVAILABLE",
                "SOLD_OUT",
                "CANCELLED",
                "NO_RESULT",
                "SOURCE_FAILURE",
                "UNKNOWN",
                name="availability_status",
            ),
            nullable=False,
        ),
        sa.Column("flight_identity_input", sa.Text(), nullable=True),
        sa.Column("flight_identity", sa.String(length=64), nullable=True),
        sa.Column(
            "quality_status",
            enum_values(
                "ELIGIBLE", "ELIGIBLE_FLAGGED", "EXCLUDED", "MANUAL_REVIEW", name="quality_status"
            ),
            nullable=False,
        ),
        sa.Column("quality_flags", json_type, nullable=False),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("included_in_index", sa.Boolean(), nullable=False),
        sa.Column("exclusion_reason", sa.Text(), nullable=True),
        sa.Column("normalization_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("advance_days >= 0", name="ck_observations_advance_nonnegative"),
        sa.CheckConstraint(
            "included_in_index OR exclusion_reason IS NOT NULL",
            name="ck_observations_exclusion_reason",
        ),
        sa.CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100)",
            name="ck_observations_quality_score_range",
        ),
        sa.CheckConstraint(
            "total_fare IS NULL OR total_fare >= 0",
            name="ck_observations_total_nonnegative",
        ),
        sa.ForeignKeyConstraint(["raw_quote_id"], ["raw_quotes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_quote_id"),
    )
    op.create_index(
        op.f("ix_fare_observations_advance_window"), "fare_observations", ["advance_window"]
    )
    op.create_index(
        op.f("ix_fare_observations_destination_iata"), "fare_observations", ["destination_iata"]
    )
    op.create_index(
        op.f("ix_fare_observations_flight_identity"), "fare_observations", ["flight_identity"]
    )
    op.create_index(
        op.f("ix_fare_observations_included_in_index"), "fare_observations", ["included_in_index"]
    )
    op.create_index(
        op.f("ix_fare_observations_methodological_date"),
        "fare_observations",
        ["methodological_date"],
    )
    op.create_index(
        op.f("ix_fare_observations_observed_at_utc"), "fare_observations", ["observed_at_utc"]
    )
    op.create_index(op.f("ix_fare_observations_origin_iata"), "fare_observations", ["origin_iata"])
    op.create_index(op.f("ix_fare_observations_travel_date"), "fare_observations", ["travel_date"])


def downgrade() -> None:
    op.drop_index(op.f("ix_fare_observations_travel_date"), table_name="fare_observations")
    op.drop_index(op.f("ix_fare_observations_origin_iata"), table_name="fare_observations")
    op.drop_index(op.f("ix_fare_observations_observed_at_utc"), table_name="fare_observations")
    op.drop_index(op.f("ix_fare_observations_methodological_date"), table_name="fare_observations")
    op.drop_index(op.f("ix_fare_observations_included_in_index"), table_name="fare_observations")
    op.drop_index(op.f("ix_fare_observations_flight_identity"), table_name="fare_observations")
    op.drop_index(op.f("ix_fare_observations_destination_iata"), table_name="fare_observations")
    op.drop_index(op.f("ix_fare_observations_advance_window"), table_name="fare_observations")
    op.drop_table("fare_observations")
    op.drop_index(op.f("ix_raw_quotes_source_id"), table_name="raw_quotes")
    op.drop_index(op.f("ix_raw_quotes_observed_at_utc"), table_name="raw_quotes")
    op.drop_index(op.f("ix_raw_quotes_content_hash"), table_name="raw_quotes")
    op.drop_index(op.f("ix_raw_quotes_collection_job_id"), table_name="raw_quotes")
    op.drop_table("raw_quotes")
    op.drop_index(op.f("ix_collection_jobs_advance_window"), table_name="collection_jobs")
    op.drop_index(op.f("ix_collection_jobs_travel_date"), table_name="collection_jobs")
    op.drop_index(op.f("ix_collection_jobs_source_id"), table_name="collection_jobs")
    op.drop_index(op.f("ix_collection_jobs_route_id"), table_name="collection_jobs")
    op.drop_index(op.f("ix_collection_jobs_collection_run_id"), table_name="collection_jobs")
    op.drop_table("collection_jobs")
    op.drop_table("collection_runs")
    op.drop_table("routes")
    op.drop_index(op.f("ix_sources_code"), table_name="sources")
    op.drop_table("sources")

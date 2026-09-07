from __future__ import annotations

import io
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast

import xlsxwriter  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import DataClass
from app.indexing.methodology import METHODOLOGY_VERSION
from app.indexing.periods import MISSING_DATA_POLICY
from app.models import (
    DailyIndex,
    FareObservation,
    HistoricalDataset,
    PeriodIndex,
    RawQuote,
)
from app.services.aggregation import index_coverage_response
from app.services.historical import build_backtest, dataset_response

NUMERIC_EXPORT_COLUMNS = {
    "index_value",
    "coverage_percent",
    "average_coverage_percent",
    "minimum_coverage_percent",
    "total_fare",
    "internal_rebased",
    "reference_rebased",
    "deviation_points",
    "deviation_percent",
    "internal_coverage_percent",
}


def _decimal(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _daily_row(index: DailyIndex) -> dict[str, object]:
    return {
        "daily_index_id": str(index.id),
        "collection_run_id": str(index.collection_run_id),
        "methodological_date": index.methodological_date.isoformat(),
        "data_class": index.data_class.value,
        "index_value": _decimal(index.index_value),
        "coverage_percent": str(index.coverage_percent),
        "publication_status": index.publication_status.value,
        "methodology_version": index.methodology_version,
        "canonicalization_version": index.canonicalization_version,
        "calculated_at": index.calculated_at.isoformat(),
    }


def _period_row(index: PeriodIndex) -> dict[str, object]:
    return {
        "period_index_id": str(index.id),
        "period_type": index.period_type.value,
        "period_start": index.period_start.isoformat(),
        "period_end": index.period_end.isoformat(),
        "data_class": index.data_class.value,
        "index_value": _decimal(index.index_value),
        "average_coverage_percent": str(index.average_coverage_percent),
        "minimum_coverage_percent": str(index.minimum_coverage_percent),
        "expected_day_count": index.expected_day_count,
        "observed_day_count": index.observed_day_count,
        "valued_day_count": index.valued_day_count,
        "low_coverage_day_count": index.low_coverage_day_count,
        "source_count": index.source_count,
        "confidence_level": index.confidence_level.value,
        "aggregation_status": index.aggregation_status.value,
        "warnings": list(index.warnings),
        "methodology_version": index.methodology_version,
        "missing_data_policy": index.missing_data_policy,
        "calculated_at": index.calculated_at.isoformat(),
    }


def build_json_export(
    session: Session,
    *,
    data_class: DataClass,
    dataset_code: str | None,
) -> dict[str, object]:
    generated_at = datetime.now(UTC)
    daily = list(
        session.scalars(
            select(DailyIndex)
            .where(DailyIndex.data_class == data_class)
            .order_by(DailyIndex.methodological_date)
        )
    )
    periods = list(
        session.scalars(
            select(PeriodIndex)
            .where(PeriodIndex.data_class == data_class)
            .order_by(PeriodIndex.period_start, PeriodIndex.period_type)
        )
    )
    observations = session.execute(
        select(FareObservation, RawQuote)
        .join(RawQuote, FareObservation.raw_quote_id == RawQuote.id)
        .where(RawQuote.data_class == data_class)
        .order_by(FareObservation.methodological_date, FareObservation.id)
    ).all()
    datasets = list(session.scalars(select(HistoricalDataset).order_by(HistoricalDataset.code)))
    latest_coverage = None if not daily else index_coverage_response(session, daily[-1]).model_dump(
        mode="json"
    )
    backtest = None
    if dataset_code is not None:
        backtest = build_backtest(
            session, dataset_code=dataset_code, data_class=data_class
        ).model_dump(mode="json")
    return {
        "metadata": {
            "generated_at": generated_at.isoformat(),
            "data_class": data_class.value,
            "methodology_version": METHODOLOGY_VERSION,
            "missing_data_policy": MISSING_DATA_POLICY,
            "format_version": "phase-15-export-v1",
        },
        "daily_indices": [_daily_row(row) for row in daily],
        "period_indices": [_period_row(row) for row in periods],
        "current_coverage": latest_coverage,
        "fare_observations": [
            {
                "observation_id": str(observation.id),
                "raw_quote_id": str(observation.raw_quote_id),
                "source_id": str(raw.source_id),
                "methodological_date": observation.methodological_date.isoformat(),
                "observed_at_utc": observation.observed_at_utc.isoformat(),
                "route": f"{observation.origin_iata}-{observation.destination_iata}",
                "travel_date": observation.travel_date.isoformat(),
                "advance_window": observation.advance_window.value,
                "flight_identity": observation.flight_identity,
                "total_fare": _decimal(observation.total_fare),
                "quality_status": observation.quality_status.value,
                "quality_flags": list(observation.quality_flags),
                "included_in_index": observation.included_in_index,
                "exclusion_reason": observation.exclusion_reason,
                "normalization_version": observation.normalization_version,
                "parser_version": raw.parser_version,
                "content_hash": raw.content_hash,
            }
            for observation, raw in observations
        ],
        "historical_datasets": [
            dataset_response(session, row).model_dump(mode="json") for row in datasets
        ],
        "backtest": backtest,
    }


def _write_table(
    sheet: Any,
    workbook: Any,
    headers: list[str],
    rows: list[list[object | None]],
) -> None:
    header = workbook.add_format(
        {"bold": True, "font_color": "#FFFFFF", "bg_color": "#17212B", "border": 0}
    )
    number_format = workbook.add_format({"num_format": "0.0000"})
    date_format = workbook.add_format({"num_format": "yyyy-mm-dd"})
    datetime_format = workbook.add_format({"num_format": "yyyy-mm-dd hh:mm:ss"})
    sheet.hide_gridlines(2)
    sheet.freeze_panes(1, 0)
    for column, header_name in enumerate(headers):
        sheet.write(0, column, header_name, header)
    for row_number, values in enumerate(rows, start=1):
        for column, value in enumerate(values):
            column_name = headers[column]
            if isinstance(value, str) and column_name in NUMERIC_EXPORT_COLUMNS:
                sheet.write_number(row_number, column, float(Decimal(value)), number_format)
            elif isinstance(value, str) and column_name in {
                "methodological_date",
                "travel_date",
                "period_start",
                "period_end",
            }:
                sheet.write_datetime(
                    row_number,
                    column,
                    datetime.combine(date.fromisoformat(value), datetime.min.time()),
                    date_format,
                )
            elif isinstance(value, str) and column_name in {
                "generated_at",
                "calculated_at",
                "observed_at_utc",
            }:
                sheet.write_datetime(
                    row_number,
                    column,
                    datetime.fromisoformat(value).replace(tzinfo=None),
                    datetime_format,
                )
            elif isinstance(value, Decimal):
                sheet.write_number(row_number, column, float(value), number_format)
            elif isinstance(value, date):
                sheet.write_datetime(
                    row_number,
                    column,
                    datetime.combine(value, datetime.min.time()),
                    date_format,
                )
            else:
                sheet.write(row_number, column, value)
    for column, name in enumerate(headers):
        maximum = max(
            [len(name), *[len(str(row[column] or "")) for row in rows]],
            default=len(name),
        )
        sheet.set_column(column, column, min(max(maximum + 2, 11), 42))
    if rows:
        sheet.autofilter(0, 0, len(rows), len(headers) - 1)


def build_excel_export(
    session: Session,
    *,
    data_class: DataClass,
    dataset_code: str | None,
) -> bytes:
    package = build_json_export(session, data_class=data_class, dataset_code=dataset_code)
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    metadata = workbook.add_worksheet("Metadata")
    metadata.hide_gridlines(2)
    metadata.set_column("A:A", 28)
    metadata.set_column("B:B", 68)
    metadata_payload = cast(dict[str, object], package["metadata"])
    metadata_rows = [[key, value] for key, value in metadata_payload.items()]
    metadata_rows.extend(
        [
            ["reference_dataset", dataset_code or "Not selected"],
            ["data_note", "Synthetic, historical, recorded-demo and live series remain separate."],
        ]
    )
    _write_table(metadata, workbook, ["Field", "Value"], metadata_rows)

    daily = cast(list[dict[str, object]], package["daily_indices"])
    daily_headers = list(daily[0]) if daily else list(_daily_row_columns())
    _write_table(
        workbook.add_worksheet("Daily APIx"),
        workbook,
        daily_headers,
        [[row.get(key) for key in daily_headers] for row in daily],
    )
    periods = cast(list[dict[str, object]], package["period_indices"])
    period_headers = list(periods[0]) if periods else list(_period_row_columns())
    _write_table(
        workbook.add_worksheet("Period APIx"),
        workbook,
        period_headers,
        [
            [
                ", ".join(value) if isinstance(value, list) else value
                for value in [row.get(key) for key in period_headers]
            ]
            for row in periods
        ],
    )
    observations = cast(list[dict[str, object]], package["fare_observations"])
    observation_headers = list(observations[0]) if observations else [
        "observation_id",
        "raw_quote_id",
        "source_id",
        "methodological_date",
        "route",
        "total_fare",
        "quality_status",
        "included_in_index",
    ]
    _write_table(
        workbook.add_worksheet("Observations"),
        workbook,
        observation_headers,
        [
            [
                ", ".join(value) if isinstance(value, list) else value
                for value in [row.get(key) for key in observation_headers]
            ]
            for row in observations
        ],
    )
    reference_rows: list[list[object | None]] = []
    datasets = cast(list[dict[str, Any]], package["historical_datasets"])
    for dataset in datasets:
        for row in cast(list[dict[str, object]], dataset["observations"]):
            reference_rows.append(
                [
                    dataset["code"],
                    dataset["publisher"],
                    dataset["source_url"],
                    row["period_start"],
                    row["period_end"],
                    row["scope_type"],
                    row["origin_iata"],
                    row["destination_iata"],
                    row["index_value"],
                    row["coverage_percent"],
                    row["status"],
                    row["source_record_id"],
                ]
            )
    _write_table(
        workbook.add_worksheet("Reference data"),
        workbook,
        [
            "dataset_code",
            "publisher",
            "source_url",
            "period_start",
            "period_end",
            "scope_type",
            "origin_iata",
            "destination_iata",
            "index_value",
            "coverage_percent",
            "status",
            "source_record_id",
        ],
        reference_rows,
    )
    backtest_rows: list[list[object | None]] = []
    backtest = cast(dict[str, Any] | None, package["backtest"])
    if backtest is not None:
        for row in cast(list[dict[str, object]], backtest["points"]):
            backtest_rows.append(
                [
                    row["period_start"],
                    row["period_end"],
                    row["internal_rebased"],
                    row["reference_rebased"],
                    row["deviation_points"],
                    row["deviation_percent"],
                    row["internal_coverage_percent"],
                    row["internal_status"],
                    row["reference_status"],
                ]
            )
    _write_table(
        workbook.add_worksheet("Back-test"),
        workbook,
        [
            "period_start",
            "period_end",
            "internal_rebased",
            "reference_rebased",
            "deviation_points",
            "deviation_percent",
            "internal_coverage_percent",
            "internal_status",
            "reference_status",
        ],
        backtest_rows,
    )
    workbook.close()
    return output.getvalue()


def _daily_row_columns() -> tuple[str, ...]:
    return (
        "daily_index_id",
        "collection_run_id",
        "methodological_date",
        "data_class",
        "index_value",
        "coverage_percent",
        "publication_status",
        "methodology_version",
        "canonicalization_version",
        "calculated_at",
    )


def _period_row_columns() -> tuple[str, ...]:
    return (
        "period_index_id",
        "period_type",
        "period_start",
        "period_end",
        "data_class",
        "index_value",
        "average_coverage_percent",
        "minimum_coverage_percent",
        "expected_day_count",
        "observed_day_count",
        "valued_day_count",
        "low_coverage_day_count",
        "source_count",
        "confidence_level",
        "aggregation_status",
        "warnings",
        "methodology_version",
        "missing_data_policy",
        "calculated_at",
    )

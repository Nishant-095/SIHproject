from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.domain.enums import DataClass, RunTrigger
from app.indexing.service import calculate_index_for_run
from app.models import BasketVersion
from app.services.collection import CollectionService
from app.services.historical import build_backtest, import_historical_dataset, payload_from_csv

MOSPI_SOURCE_URL = "https://cpi.mospi.gov.in/PDFile/Press/PR%20October%202025.pdf"


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Create a clearly labelled 30-day synthetic back-test demonstration"
    )
    command.add_argument("--start-date", type=date.fromisoformat, default=date(2025, 9, 15))
    command.add_argument("--days", type=int, default=30)
    command.add_argument(
        "--reference-csv",
        type=Path,
        default=Path("data/reference/mospi-airfare-cpi-sample.csv"),
    )
    return command


async def run(start_date: date, days: int, reference_csv: Path) -> dict[str, object]:
    if days < 30:
        raise ValueError("the Phase 14 demonstration requires at least 30 days")
    settings = get_settings()
    with SessionLocal() as session:
        existing_basket = session.scalar(
            select(BasketVersion).where(
                BasketVersion.data_class == DataClass.SYNTHETIC,
                BasketVersion.active.is_(True),
            )
        )
        if (
            existing_basket is not None
            and existing_basket.base_start_date is not None
            and existing_basket.base_start_date > start_date
        ):
            raise ValueError(
                "the active synthetic base starts after this scenario; "
                "run the demonstration against a clean database"
            )
        payload = payload_from_csv(
            reference_csv.read_text(encoding="utf-8-sig"),
            code="MOSPI-AIRFARE-CPI-2012-2025-10-SAMPLE",
            title="MoSPI All India CPI air fare item sample",
            publisher="Ministry of Statistics and Programme Implementation",
            source_url=MOSPI_SOURCE_URL,
            license_name="Government Open Data License - India",
            metric_name="Air fare (normal): economy class (adult), All India Combined CPI",
            frequency="MONTHLY",
            base_period="2012=100",
            notes="Four values transcribed from Annexure V of the October 2025 CPI release.",
        )
        dataset, _ = import_historical_dataset(session, payload)
        service = CollectionService(settings)
        created_indices = 0
        for offset in range(days):
            planned = await service.run_fixture(
                session,
                methodological_date=start_date + timedelta(days=offset),
                trigger=RunTrigger.BACKFILL,
            )
            result = calculate_index_for_run(session, planned.run.id)
            created_indices += int(result.created)
        report = build_backtest(
            session,
            dataset_code=dataset.code,
            data_class=DataClass.SYNTHETIC,
        )
        return {
            "data_class": DataClass.SYNTHETIC.value,
            "start_date": start_date.isoformat(),
            "end_date": (start_date + timedelta(days=days - 1)).isoformat(),
            "requested_days": days,
            "new_daily_indices": created_indices,
            "dataset_code": dataset.code,
            "overlap_month_count": report.overlap_month_count,
            "correlation": None if report.correlation is None else str(report.correlation),
            "correlation_status": report.correlation_status,
            "warnings": report.warnings,
        }


def main() -> None:
    args = parser().parse_args()
    print(json.dumps(asyncio.run(run(args.start_date, args.days, args.reference_csv)), indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db.session import SessionLocal
from app.services.historical import dataset_response, import_historical_dataset, payload_from_csv


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Import a provenance-aware reference index CSV")
    command.add_argument("csv_path", type=Path)
    command.add_argument("--code", required=True)
    command.add_argument("--title", required=True)
    command.add_argument("--publisher", required=True)
    command.add_argument("--source-url", required=True)
    command.add_argument("--license", dest="license_name", required=True)
    command.add_argument("--metric", dest="metric_name", required=True)
    command.add_argument("--frequency", choices=("DAILY", "MONTHLY"), default="MONTHLY")
    command.add_argument("--base-period")
    command.add_argument("--notes")
    return command


def main() -> None:
    args = parser().parse_args()
    payload = payload_from_csv(
        args.csv_path.read_text(encoding="utf-8-sig"),
        code=args.code,
        title=args.title,
        publisher=args.publisher,
        source_url=args.source_url,
        license_name=args.license_name,
        metric_name=args.metric_name,
        frequency=args.frequency,
        base_period=args.base_period,
        notes=args.notes,
    )
    with SessionLocal() as session:
        dataset, created = import_historical_dataset(session, payload)
        result = dataset_response(session, dataset, include_observations=False).model_dump(
            mode="json"
        )
        result["created"] = created
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.indexing.service import calculate_index_for_run
from app.services.collection import CollectionService
from app.services.seed import seed_configuration


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Airfare APIx development commands")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed", help="Create the frozen routes and fixture source")
    demo = commands.add_parser("demo-run", help="Run the deterministic synthetic pipeline")
    demo.add_argument("--date", type=date.fromisoformat, dest="methodological_date")
    real = commands.add_parser("duffel-run", help="Run the configured Duffel API pipeline")
    real.add_argument("--date", type=date.fromisoformat, dest="methodological_date")
    web = commands.add_parser(
        "web-run",
        help="Run the configured permissioned web-extraction pipeline",
    )
    web.add_argument("--date", type=date.fromisoformat, dest="methodological_date")
    apix = commands.add_parser("apix-run", help="Calculate and persist Phase 8 APIx for one run")
    apix.add_argument("--run-id", type=uuid.UUID, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    with SessionLocal() as session:
        if args.command == "seed":
            seed_configuration(session, settings)
            return

        if args.command == "apix-run":
            apix_result = calculate_index_for_run(session, args.run_id)
            index = apix_result.daily_index
            print(
                json.dumps(
                    {
                        "daily_index_id": str(index.id),
                        "created": apix_result.created,
                        "collection_run_id": str(index.collection_run_id),
                        "methodological_date": index.methodological_date.isoformat(),
                        "data_class": index.data_class.value,
                        "methodology_version": index.methodology_version,
                        "index_value": None
                        if index.index_value is None
                        else str(index.index_value),
                        "coverage_percent": str(index.coverage_percent),
                        "publication_status": index.publication_status.value,
                    },
                    indent=2,
                )
            )
            return

        methodological_date = (
            args.methodological_date or datetime.now(ZoneInfo(settings.collection_timezone)).date()
        )
        service = CollectionService(settings)
        operations = {
            "demo-run": service.run_fixture,
            "duffel-run": service.run_duffel,
            "web-run": service.run_permissioned_web,
        }
        operation = operations[args.command]
        collection_result = asyncio.run(
            operation(
                session,
                methodological_date=methodological_date,
            )
        )
        output = {
            "run_id": str(collection_result.run.id),
            "created": collection_result.created,
            "status": collection_result.run.status.value,
            "data_class": collection_result.run.data_class.value,
            "planned_jobs": collection_result.run.planned_jobs,
            "successful_jobs": collection_result.run.successful_jobs,
            "failed_jobs": collection_result.run.failed_jobs,
            "valid_observations": collection_result.run.valid_observations,
        }
        print(json.dumps(output, indent=2))  # CLI output is intentionally human-readable.


if __name__ == "__main__":
    main()

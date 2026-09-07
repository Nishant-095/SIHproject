from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect


def test_migration_upgrade_downgrade_upgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "migration-check.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    environment = {**os.environ, "DATABASE_URL": database_url, "SCHEDULER_ENABLED": "false"}

    for target in ("head", "base", "head"):
        action = "upgrade" if target == "head" else "downgrade"
        subprocess.run(
            [sys.executable, "-m", "alembic", action, target],
            cwd=Path(__file__).parents[1],
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )

    inspector = inspect(create_engine(database_url))
    tables = set(inspector.get_table_names())
    assert tables >= {
        "sources",
        "routes",
        "collection_runs",
        "collection_jobs",
        "raw_quotes",
        "fare_observations",
        "canonical_fares",
        "canonical_fare_observations",
        "basket_versions",
        "basket_items",
        "daily_route_window_prices",
        "route_window_price_inputs",
        "daily_indices",
        "daily_index_components",
        "period_indices",
        "period_index_inputs",
        "historical_datasets",
        "historical_index_observations",
    }
    observation_indexes = {
        tuple(index["column_names"]) for index in inspector.get_indexes("fare_observations")
    }
    assert ("origin_iata", "destination_iata") in observation_indexes
    assert ("carrier_code",) in observation_indexes

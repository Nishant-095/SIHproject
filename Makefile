VENV := $(CURDIR)/.venv

.PHONY: install backend-install frontend-install migrate seed demo duffel web apix historical backtest test lint typecheck build up down

install: backend-install frontend-install

backend-install:
	python3 -m venv .venv
	$(VENV)/bin/pip install -e './backend[dev]'

frontend-install:
	npm --prefix frontend install

migrate:
	$(VENV)/bin/alembic -c backend/alembic.ini upgrade head

seed:
	cd backend && $(VENV)/bin/python -m app.cli seed

demo:
	cd backend && $(VENV)/bin/python -m app.cli demo-run

duffel:
	cd backend && $(VENV)/bin/python -m app.cli duffel-run

web:
	cd backend && $(VENV)/bin/python -m app.cli web-run

apix:
	cd backend && $(VENV)/bin/python -m app.cli apix-run --run-id $(RUN_ID)

historical:
	PYTHONPATH=backend $(VENV)/bin/python scripts/import_historical.py $(CSV) --code $(CODE) --title "$(TITLE)" --publisher "$(PUBLISHER)" --source-url "$(SOURCE_URL)" --license "$(LICENSE)" --metric "$(METRIC)"

backtest:
	PYTHONPATH=backend $(VENV)/bin/python scripts/run_30_day_backtest.py

test:
	cd backend && $(VENV)/bin/pytest
	npm --prefix frontend run test

lint:
	cd backend && $(VENV)/bin/ruff check app tests alembic/versions
	npm --prefix frontend run lint

typecheck:
	cd backend && $(VENV)/bin/mypy app
	npm --prefix frontend run typecheck

build:
	npm --prefix frontend run build

up:
	docker compose up --build

down:
	docker compose down

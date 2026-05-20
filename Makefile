SHELL := /bin/bash

DB_URL ?= postgresql://postgres:postgres@127.0.0.1:55432/gym_schedule

.PHONY: help deps db-up db-down init-db seed api bootstrap

help:
	@echo "Available targets:"
	@echo "  make deps       - install/sync Python dependencies"
	@echo "  make db-up      - start PostgreSQL container via docker compose"
	@echo "  make db-down    - stop PostgreSQL container and compose resources"
	@echo "  make init-db    - create DB schema"
	@echo "  make seed       - apply PostgreSQL seed script"
	@echo "  make api        - run FastAPI server with reload"
	@echo "  make bootstrap  - db-up + deps + init-db + seed"

deps:
	uv sync

db-up:
	@if docker ps --filter "publish=55432" --format '{{.Names}}' | grep -q .; then \
		echo "Port 55432 already in use by running container(s):"; \
		docker ps --filter "publish=55432" --format '  - {{.Names}}'; \
		echo "Reusing existing PostgreSQL instance."; \
	else \
		docker compose up -d db; \
	fi

db-down:
	docker compose down

init-db:
	uv run python scripts/init_db.py

seed:
	psql "$(DB_URL)" -f sql/seed_firebase_user_postgres.sql

api:
	uv run python scripts/run_api.py --reload

bootstrap: db-up deps init-db seed

# AGENTS.md — FitnessCenter API

FastAPI backend; single source of truth for the Flutter mobile app (members) and
the Nuxt admin web (staff). One role-aware, multi-tenant service: auth,
scheduling, bookings, content, notifications, membership. See `README.md` for the
full architecture narrative — this file is the agent operating guide.

## Stack

FastAPI 0.135 · Python ≥3.12 · Pydantic v2 · SQLAlchemy 2.0 · Alembic ·
Firebase Admin (Auth + Cloud Messaging) · PostgreSQL · `uv` for deps.

## Layout (`app/`)

Layered, feature-modular: **routers → services → repositories**.
- `routers/` — HTTP concerns only (request/response, status codes, deps).
- `services/` — business logic; `services/validators/` for input validation.
- `repositories/` — persistence; the only layer that touches the ORM.
- `domain/` — domain models/entities.
- `schemas/` — Pydantic DTOs (see DTO rules below).
- `core/` — cross-cutting: config, auth, tenancy, `push.py` (FCM).
- `alembic/versions/` — migrations **and** idempotent seed data.

## Commands

```bash
uv sync                                  # install deps
docker compose up -d db                  # PostgreSQL on host port 55432
uv run python scripts/run_api.py --reload
make bootstrap && make api               # one-command flow
```
Make targets: `db-up`, `db-down`, `deps`, `seed`, `api`, `bootstrap`.
- API base: `http://127.0.0.1:8000/api/v1` · Docs: `/docs`
- Default DB: `postgresql+psycopg://postgres:postgres@127.0.0.1:55432/gym_schedule`

## Conventions & rules

- **Keep layers separate.** Routers never query the ORM; only repositories do.
  Business rules live in services, not routers or repositories.
- **DTO layer convention** — `schemas/` are DTOs. Outbound: build responses with
  a `from_model` classmethod (model → DTO). Inbound: consume with `model_dump()`
  / factory rules. Don't hand-map fields ad hoc.
- **Auth is Firebase-verified, DB-authorized.** Firebase verifies the ID token;
  the role/permissions come from the database and are written as custom claims.
  Never trust a client-supplied role.
- **Origin gating** — `POST /auth/firebase-login` requires header
  `X-Client-Platform: mobile | web` (members→mobile, staff→web). Mismatch → 403,
  missing/unknown → 400. Preserve this when touching auth.
- **Multi-tenancy is enforced at the ORM session layer** — tenant-scoped queries
  auto-filter by company and inserts auto-stamp. Do not add manual `company_id`
  filtering that bypasses or double-applies this; do not write queries that can
  cross tenants.
- **Seeding is one transaction.** The whole Alembic seed runs in a single
  transaction — a later failed insert silently discards everything. Seeds are
  idempotent (`ON CONFLICT` / `NOT EXISTS`), keyed by company slug from
  `credentials/demo_users.json`. Test seed changes end to end after edits.
- Schema/migrations: change models, then add an Alembic migration. The lifespan
  handler creates schema on startup and applies seed migrations.

## Do not

- Commit anything under `credentials/` or real `.env` values / service accounts.
- Pin/upgrade the dependency versions in `pyproject.toml` without being asked —
  they are exact-pinned on purpose.
- Edit `alembic/versions/__pycache__` or generated artifacts.

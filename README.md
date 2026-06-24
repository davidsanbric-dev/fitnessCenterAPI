# FitnessCenter API

FastAPI backend powering the **FitnessCenter Suite** — the single source of truth for the Flutter mobile app (members) and the Nuxt.js admin web (staff). One role-aware, multi-tenant service handles auth, scheduling, bookings, content, notifications, and membership.

## Architecture

Clean, layered, and feature-modular — built to stay scalable and maintainable:

- **Routers → Services → Repositories** — HTTP concerns, business logic, and persistence are separated; each feature domain (`auth`, `bookings`, `classes`, `disciplines`, `trainers`, `memberships`, `notifications`, `blog`, `admin`) is its own module.
- **Firebase-backed identity, DB-driven authorization** — Firebase verifies ID tokens; the backend resolves the role/permissions from the database and writes them as custom claims. Credentials live in Firebase, authorization lives here.
- **Origin gating** — `POST /auth/firebase-login` enforces an `X-Client-Platform: mobile | web` header so members sign in only from mobile and staff only from web. Mismatch → `403`; missing/unknown → `400`. The role is resolved from the verified token, so it can never elevate.
- **Multi-tenancy at the ORM session layer** — every tenant-scoped query is auto-filtered by company and every insert auto-stamped, so business code can't cross tenants by accident.
- **Event-driven notifications** — member booking/cancellation events create staff/trainer inbox notifications; staff actions (blog publish, announcements, status changes) dispatch FCM push to members via `app/core/push.py`.

## Multi-tenant seeding (per recruiter/tester)

Seed data runs via Alembic on startup and is driven by `credentials/demo_users.json`, keyed by **company slug**:

```json
{
  "otrofy":    { "admin": "admin@...:pw", "member": "alex@...:pw", "trainer": "jordan@...:pw" },
  "sebastian": { "admin": "admin@...:pw", "member": "alex@...:pw", "trainer": "jordan@...:pw" }
}
```

Each top-level entry provisions one **isolated, identically-shaped company** (disciplines, plans, class catalog, a staff trainer with starter slots, blog, booking history). The seed is **idempotent** (`ON CONFLICT` / `NOT EXISTS`): adding a slug and restarting provisions only the newcomer, leaving existing tenants untouched. This is how each tester/recruiter gets their own private gym to explore the full suite.

## Tech stack

**FastAPI · Python · PostgreSQL · SQLAlchemy · Alembic · Firebase Admin (Auth + Cloud Messaging)**

## Run

```bash
cp .env.example .env          # set DATABASE_URL, FIREBASE_* and demo_users path
docker compose up -d db       # PostgreSQL on host port 55432
uv sync
uv run python scripts/run_api.py --reload
```

Or the one-command flow: `make bootstrap && make api` (`Makefile` targets: `db-up`, `db-down`, `deps`, `seed`, `api`, `bootstrap`).

- API base URL: `http://127.0.0.1:8000/api/v1`
- Interactive docs (OpenAPI / Swagger UI): `http://127.0.0.1:8000/docs`

### Firebase configuration

Set one of:

- `FIREBASE_SERVICE_ACCOUNT_PATH=/absolute/path/to/service-account.json`
- Application Default Credentials in the runtime environment

Optional: `FIREBASE_PROJECT_ID=<firebase-project-id>`.

## Notes

- The lifespan handler creates the schema on startup, then applies Alembic seed migrations.
- Default DB: `postgresql+psycopg://postgres:postgres@127.0.0.1:55432/gym_schedule` (custom host port avoids conflicts).
- `make db-up` reuses an existing container bound to `55432` instead of failing.
- Override any setting via environment variables or a local `.env`.

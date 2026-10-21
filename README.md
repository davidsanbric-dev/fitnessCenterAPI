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

## Demo tenants

Each top-level key in `credentials/demo_users.json` becomes an isolated company
(a `target_companies` row) and receives the same Spanish reference catalog:
disciplines, membership plans, five trainers, six class types, a rolling
weekday timetable for the next three weeks, and three blog posts.

### Adding a reviewer-facing tenant

The file is gitignored, so add the tenant locally. Omit the `admin` key: a
tenant with no admin account has nothing to escalate to, which is what you want
for credentials you hand to someone outside the team.

```jsonc
{
  "demo": {
    "member":  "socio.demo@example.cl:<password>",
    "trainer": "entrenador.demo@example.cl:<password>"
  }
}
```

The `trainer` entry is optional but recommended: it provisions the staff
trainer, their one-on-one availability and three past sessions, so the member's
history and profile screens have content instead of being empty.

Members not listed in `_DEMO_MEMBER_PROFILES` (`app/core/seed.py`) get
deterministic placeholder personal data, which reads as placeholder on the
profile screen. To give the demo member realistic details, add an entry keyed
by the email local-part:

```python
"socio.demo": {
    "first_name": "Valentina",
    "paternal_surname": "Soto",
    "maternal_surname": "Morales",
    "rut": "19876543-2",
    "mobile_phone": "+56912345678",
    "birth_date": "1995-04-18",
    "address": "Av. Apoquindo 1234, Las Condes, Santiago",
    "fitness_goals": "Ganar fuerza y mantener una rutina constante de clases grupales.",
}
```

Note the ordering constraint: every `_DEMO_MEMBER_PROFILES` key **must** match a
member in `demo_users.json`, or the seed raises. Add the tenant first.

### Verifying seed changes

`scripts/seed_smoke_test.py` provisions a scratch database, seeds it twice and
diffs the row counts, which catches a non-idempotent statement. The whole seed
runs in one transaction, so a statement that re-inserts on the second run can
silently discard everything before it.

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:55432/gym_schedule_seedtest \
    uv run python scripts/seed_smoke_test.py
```

It refuses to run unless the database name contains `seedtest`.

### Resetting a tenant

The timetable is anchored to `CURRENT_DATE` when it is seeded, so a demo left
alone eventually shows an empty availability screen. Reset clears that tenant's
bookings and slots, zeroes its booking counters and re-seeds the timetable from
today. Catalog, users, profiles and memberships are preserved.

```bash
uv run python scripts/reset_demo_tenant.py --slug demo --dry-run
uv run python scripts/reset_demo_tenant.py --slug demo
```

Scoped to one slug and refuses to run without one, so it cannot fan out across
tenants.

## Notes

- The lifespan handler creates the schema on startup, then applies Alembic seed migrations.
- Default DB: `postgresql+psycopg://postgres:postgres@127.0.0.1:55432/gym_schedule` (custom host port avoids conflicts).
- `make db-up` reuses an existing container bound to `55432` instead of failing.
- Override any setting via environment variables or a local `.env`.

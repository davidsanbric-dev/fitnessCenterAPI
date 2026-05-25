# `project_api`

Gym scheduling backend generated from the clinic-to-gym adaptation contract.

## Features

- JWT auth with register, login, refresh, logout, and profile management
- Catalog endpoints for trainers, disciplines, categories, class types, and slots
- Booking flows by trainer or class type with cancellation/status updates
- Membership, notifications, static configuration, and aggregated home dashboard
- PostgreSQL default persistence with automatic table creation and sample seed data

## Run

```bash
cd /home/david/Escritorio/portfolio/project_api
uv sync
uv run python scripts/run_api.py --reload
```

Or use the one-command bootstrap flow:

```bash
cd /home/david/Escritorio/portfolio/project_api
make bootstrap
make api
```

Start PostgreSQL first (custom host port `55432` to avoid conflicts):

```bash
docker compose up -d db
```

Alternative without compose:

```bash
docker run --name gym-postgres \
	-e POSTGRES_DB=gym_schedule \
	-e POSTGRES_USER=postgres \
	-e POSTGRES_PASSWORD=postgres \
	-p 55432:5432 \
	-d postgres:17
```

Before running, initialize local env vars from the template:

```bash
cp .env.example .env
```

## API base URL

- `http://127.0.0.1:8000/api/v1`

## Firebase auth setup

- Protected routes now validate Firebase ID tokens.
- Configure one of the following before running the API:
	- `FIREBASE_SERVICE_ACCOUNT_PATH=/absolute/path/to/service-account.json`
	- Application Default Credentials available in the runtime environment.
- Optional: `FIREBASE_PROJECT_ID=<firebase-project-id>`

### Sync custom claims after Firebase sign-in

- Endpoint: `POST /api/v1/auth/firebase/sync-claims`
- Header: `Authorization: Bearer <firebase-id-token>`
- Behavior: looks up API user by Firebase token email and sets custom claims in Firebase.

### Admin web auth + lookup endpoints (additive)

- `POST /api/v1/auth/firebase-login`
	- Request: `{ "id_token": "<firebase-id-token>" }`
	- Response: backend role/permissions context for web app session bootstrap
- `GET /api/v1/users/by-email?email=<email>`
	- Requires admin/manager role (resolved from configured email lists)

### Admin dashboard endpoints (additive)

- `GET /api/v1/admin/home`
- `GET /api/v1/admin/bookings`
- `PATCH /api/v1/admin/bookings/{booking_id}/status`
- `POST /api/v1/admin/membership-plans`
- `PUT /api/v1/admin/membership-plans/{plan_id}`
- `DELETE /api/v1/admin/membership-plans/{plan_id}`

Existing member/mobile endpoints remain unchanged and available.

### Seed data

Seed data now runs via Alembic on application startup (after tables are created).


## Notes

- Default database: `postgresql+psycopg://postgres:postgres@127.0.0.1:55432/gym_schedule`
- `Makefile` targets available: `db-up`, `db-down`, `deps`, `seed`, `api`, `bootstrap`
- `make db-up` reuses an existing container already bound to `55432` instead of failing
- Override settings with environment variables or a local `.env` file
- The app automatically creates the database schema on startup (lifespan handler), then applies Alembic seed migrations
- `scripts/run_api.py` avoids `ModuleNotFoundError: app` when running outside `project_api`
- API process is long-running; run seed in a separate terminal or before starting the server

## Related Migration Docs

- Flutter clinic->gym migration map:
	`../portfolio_mobile_app/MIGRATION_MAP.md`

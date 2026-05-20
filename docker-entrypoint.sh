#!/bin/bash
set -e

# Parse DATABASE_URL to get connection parameters
# Format: postgresql+psycopg://user:password@host:port/dbname
DB_URL=$(echo "$DATABASE_URL" | sed 's/+psycopg://')
DB_USER=$(echo "$DB_URL" | cut -d: -f2 | cut -d/ -f3 | cut -d@ -f1)
DB_PASSWORD=$(echo "$DB_URL" | cut -d: -f3 | cut -d@ -f1)
DB_HOST_PORT=$(echo "$DB_URL" | cut -d@ -f2 | cut -d/ -f1)
DB_NAME=$(echo "$DB_URL" | cut -d/ -f4)

DB_HOST=$(echo "$DB_HOST_PORT" | cut -d: -f1)
DB_PORT=$(echo "$DB_HOST_PORT" | cut -d: -f2)

# Export PGPASSWORD for psql commands
export PGPASSWORD="$DB_PASSWORD"

# Wait for database to be ready (important for Dokploy deployments)
echo "Waiting for database to be ready at $DB_HOST:$DB_PORT..."
for i in {1..30}; do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
        echo "Database is ready!"
        break
    fi
    echo "Attempt $i/30: Database not ready yet..."
    sleep 2
done

# Run database migrations
echo "Running database initialization..."
uv run python scripts/init_db.py

# Run seed data (including Firebase user)
echo "Running database seeding..."
if [ -f "/app/sql/seed_firebase_user_postgres.sql" ]; then
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f /app/sql/seed_firebase_user_postgres.sql
    echo "Database seeding completed."
else
    echo "Warning: Seed file not found at /app/sql/seed_firebase_user_postgres.sql"
fi

# Start the application
echo "Starting application..."
exec "$@"
#!/bin/bash
set -e

# Wait for database to be ready (important for Dokploy deployments)
echo "Waiting for database to be ready..."
for i in {1..30}; do
    if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" > /dev/null 2>&1; then
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
    # Extract database connection details from DATABASE_URL
    # Format: postgresql+psycopg://user:password@host:port/dbname
    DB_URL=$(echo "$DATABASE_URL" | sed 's/+psycopg://')
    psql "$DB_URL" -f /app/sql/seed_firebase_user_postgres.sql
    echo "Database seeding completed."
else
    echo "Warning: Seed file not found at /app/sql/seed_firebase_user_postgres.sql"
fi

# Start the application
echo "Starting application..."
exec "$@"
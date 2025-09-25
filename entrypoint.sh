#!/bin/bash

# This script runs every time the API container starts.

echo "Waiting for PostgreSQL to be ready..."

# The `pg_isready` command checks the status of the PostgreSQL server.
# We use a loop to wait until the database is accepting connections.
# The database host 'db' is the service name from docker-compose.yml.
until pg_isready -h db -p 5432 -U "${POSTGRES_USER}"; do
  sleep 2
done

echo "PostgreSQL is ready!"

echo "Running database migrations..."
# Apply any pending Alembic migrations
alembic upgrade head

echo "Checking for FAISS index..."
# Check if the vector DB index exists and build it if not
if [ ! -f "app/data/medical_items.index" ]; then
    echo "FAISS index not found. Building vector database..."
    python scripts/build_vector_db.py
else
    echo "FAISS index already exists."
fi


echo "Starting FastAPI application..."
# Start the Uvicorn server, making it accessible from other containers
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

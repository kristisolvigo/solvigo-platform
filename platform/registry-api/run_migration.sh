#!/bin/bash
# Run Alembic migration via gcloud sql connect

set -e

echo "Running Alembic migration for Solvigo Registry..."
echo ""

# Get migration SQL
cd /Users/kristifrancis/Desktop/Solvigo/create-app/platform/registry-api

# Export DATABASE_URL for Alembic (even though we won't use it directly)
export DATABASE_URL="postgresql://kristi@solvigo.ai@127.0.0.1:5432/registry"

# Generate SQL from Alembic (offline mode)
echo "Generating migration SQL..."
/Users/kristifrancis/Library/Python/3.9/bin/alembic upgrade head --sql > migration.sql

echo "✓ Migration SQL generated"
echo ""
echo "Executing migration via gcloud..."
echo ""

# Execute via gcloud
gcloud sql connect solvigo-registry \
  --user=kristi@solvigo.ai \
  --database=registry \
  --project=solvigo-platform-prod \
  --quiet < migration.sql

echo ""
echo "✓ Migration complete!"
echo ""
echo "Verifying tables..."
echo ""

# List tables
gcloud sql connect solvigo-registry \
  --user=kristi@solvigo.ai \
  --database=registry \
  --project=solvigo-platform-prod \
  --quiet <<'SQL'
\dt
SQL

echo ""
echo "✅ Registry database setup complete!"

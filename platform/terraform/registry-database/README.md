# Registry Database

Cloud SQL PostgreSQL instance for the Solvigo platform registry.

## What This Creates

- Cloud SQL PostgreSQL 15 instance (db-f1-micro, ~$7/month)
- Database: `registry`
- IAM users:
  - `kristi@solvigo.ai` (superadmin)
  - `registry-api@solvigo-platform-prod.iam` (service account for API)
- Private IP connection to Shared VPC
- Automatic backups (7-day retention)

## Deploy

```bash
cd platform/terraform/registry-database
terraform init
terraform apply
```

## Connect to Database

### Via Cloud SQL Proxy (Recommended)

```bash
# Install Cloud SQL Proxy
# macOS: brew install cloud-sql-proxy

# Get connection name
terraform output instance_connection_name

# Start proxy
cloud-sql-proxy solvigo-platform-prod:europe-north1:solvigo-registry

# In another terminal, connect
psql "host=127.0.0.1 port=5432 dbname=registry user=kristi@solvigo.ai"
```

### Via gcloud

```bash
gcloud sql connect solvigo-registry \
  --project=solvigo-platform-prod \
  --user=kristi@solvigo.ai \
  --database=registry
```

## Run Alembic Migration

After the database is created:

```bash
cd ../../registry-api

# Install dependencies
pip install -r requirements.txt

# Get connection string
cd ../terraform/registry-database
export DATABASE_URL=$(terraform output -raw connection_string)

# Run migration
cd ../../registry-api
alembic upgrade head

# Verify tables created
psql $DATABASE_URL -c "\dt"
```

## Verify Permissions

```bash
# Connect as kristi@solvigo.ai
psql $DATABASE_URL

# Check grants
SELECT * FROM information_schema.table_privileges
WHERE grantee = 'kristi@solvigo.ai';

# Should show ALL PRIVILEGES on all tables
```

## Outputs

- `instance_connection_name` - For Cloud SQL Proxy
- `database_name` - Database name
- `registry_api_sa_email` - Service account for API
- `connection_string` - For Alembic/applications

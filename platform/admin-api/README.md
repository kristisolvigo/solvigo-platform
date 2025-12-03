# Solvigo Admin API

Central admin API for managing Solvigo client projects, environments, and services.

## Local Development

### Prerequisites
- Docker and Docker Compose
- Python 3.11+

### Start Local Environment

```bash
# Start PostgreSQL and API with hot-reload
docker-compose up

# API will be available at http://localhost:8081
# PostgreSQL will be available at localhost:5433
```

### Run Migrations

```bash
# Run migrations in a separate container
docker-compose run --rm migrate

# Or run manually
docker-compose up db
export DATABASE_URL=postgresql://postgres:postgres@localhost:5433/registry
alembic upgrade head
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8081/docs
- ReDoc: http://localhost:8081/redoc

### Environment Variables (Local)

The docker-compose.yml sets these automatically:
- `DATABASE_URL`: PostgreSQL connection string
- `USE_CLOUD_SQL`: false (use local PostgreSQL)
- `DEV_MODE`: true

## Production Deployment

The API deploys to Cloud Run with Cloud SQL integration.

### Cloud SQL Connection

In production, the API connects to:
- Instance: `solvigo-platform-prod:europe-north1:solvigo-registry`
- Database: `registry`
- User: `admin-api@solvigo-platform-prod.iam` (IAM auth)
- Network: Private IP via VPC connector

### Deploy via Cloud Build

```bash
gcloud builds submit --config=cloudbuild.yaml
```

This builds the Docker image and deploys to Cloud Run.

## Database Schema

See `alembic/versions/001_initial_schema.py` for the full schema.

Key tables:
- **clients** - Client companies
- **projects** - Client projects with GCP resources
- **environments** - Staging/Prod configurations
- **services** - Cloud Run services
- **deployments** - Deployment history
- **users** - Platform users
- **audit_log** - All changes tracked

## API Endpoints

### Clients
- `POST /api/v1/clients` - Register client
- `GET /api/v1/clients` - List clients
- `GET /api/v1/clients/{id}` - Get client

### Projects
- `POST /api/v1/projects` - Register project
- `GET /api/v1/projects` - List projects
- `GET /api/v1/projects/{id}` - Get project
- `DELETE /api/v1/projects/{id}` - Delete project

### Subdomains
- `GET /api/v1/subdomains` - Get all subdomain mappings
- `GET /api/v1/subdomains/{domain}` - Get specific mapping

## Development Tips

### Hot Reload
The docker-compose setup mounts `./app` and `./alembic` as volumes, so code changes are reflected immediately.

### Database Access
```bash
# Connect to local PostgreSQL
psql postgresql://postgres:postgres@localhost:5433/registry

# Or via Docker
docker-compose exec db psql -U postgres -d registry
```

### Reset Database
```bash
docker-compose down -v  # Remove volumes
docker-compose up       # Start fresh
```

## Switching Between Local and Cloud SQL

The `app/database.py` module supports both:

**Local PostgreSQL** (docker-compose):
```python
USE_CLOUD_SQL=false
DATABASE_URL=postgresql://postgres:postgres@db:5432/registry
```

**Cloud SQL** (production):
```python
USE_CLOUD_SQL=true
INSTANCE_CONNECTION_NAME=solvigo-platform-prod:europe-north1:solvigo-registry
DB_USER=admin-api@solvigo-platform-prod.iam
DB_NAME=registry
```

## CLI Integration

The Solvigo CLI uses this API via `AdminClient`:

```python
from solvigo.admin.client import AdminClient

# Production mode
client = AdminClient()

# Dev mode (local)
client = AdminClient(dev_mode=True)
```

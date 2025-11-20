# ✅ Registry Database Setup Complete!

## Summary

The Solvigo registry PostgreSQL database is now fully set up with all tables created and permissions configured.

---

## Database Details

**Instance**: `solvigo-registry`
- **Status**: ✅ RUNNABLE
- **Version**: PostgreSQL 15
- **Tier**: db-f1-micro (~$7/month)
- **Region**: europe-north1
- **Network**: Private IP only (10.39.0.3)
- **VPC**: solvigo-shared-vpc
- **IAM Auth**: Enabled
- **Backups**: Enabled (7-day retention)

**Database**: `registry`
- **Owner**: kristi@solvigo.ai
- **Tables**: 14 (13 data tables + alembic_version)
- **Migration Version**: 001

---

## Tables Created

All owned by `kristi@solvigo.ai`:

1. ✅ **clients** - Client companies
2. ✅ **projects** - Client projects
3. ✅ **environments** - Staging/Prod configurations
4. ✅ **services** - Cloud Run services
5. ✅ **deployments** - Deployment history
6. ✅ **subdomain_mappings** - Load balancer routing
7. ✅ **infrastructure_resources** - All GCP resources
8. ✅ **users** - Platform users (admins, consultants)
9. ✅ **project_access** - Per-project permissions
10. ✅ **cost_allocations** - Monthly cost tracking
11. ✅ **audit_log** - All changes tracked
12. ✅ **dns_records** - DNS configuration
13. ✅ **terraform_states** - State metadata
14. ✅ **alembic_version** - Migration tracking

---

## Users Configured

### kristi@solvigo.ai
- **Type**: CLOUD_IAM_USER
- **Role**: Superuser
- **Privileges**: ALL on all tables, sequences, functions
- **Owner**: All tables, database, public schema

### registry-api@solvigo-platform-prod.iam
- **Type**: CLOUD_IAM_SERVICE_ACCOUNT
- **Role**: Standard user
- **Privileges**: SELECT, INSERT, UPDATE, DELETE on all tables
- **Purpose**: For registry API to read/write data

---

## Migration Tracking

**Alembic Version**: 001
- Migration file: `alembic/versions/001_initial_schema.py`
- Applied: Successfully
- Tracked in: `alembic_version` table

**Future migrations** will be tracked properly with version numbers!

---

## Security Configuration

✅ **Private IP Only**: 10.39.0.3 (no public internet access)
✅ **VPC**: Connected to solvigo-shared-vpc
✅ **IAM Auth**: Passwordless authentication
✅ **Backups**: Automated daily backups
✅ **Encryption**: At rest and in transit

**Temporary public IP** was used only for migration setup and is now **disabled**.

---

## How Setup Was Done

### 1. Created Infrastructure (Terraform)
```bash
cd platform/terraform/registry-database
terraform init
terraform apply

# Created:
# - Cloud SQL instance
# - VPC peering for private services
# - Database: registry
# - IAM users
```

### 2. Ran Migration (Alembic)
```bash
# Temporarily enabled public IP
gcloud sql instances patch solvigo-registry --assign-ip

# Ran migration
export DATABASE_URL="postgresql://kristi@solvigo.ai@PUBLIC_IP:5432/registry"
alembic upgrade head

# Disabled public IP
gcloud sql instances patch solvigo-registry --no-assign-ip
```

### 3. Verified
- ✅ 14 tables created
- ✅ All owned by kristi@solvigo.ai
- ✅ Migration version tracked
- ✅ Private IP only

---

## Connecting to Database

### For Future Migrations

Since the database has private IP only, future migrations need to be run from:

**Option 1: Cloud Shell** (Inside Google network):
```bash
# Open Cloud Shell
gcloud cloud-shell ssh

# Clone repo, install alembic
cd create-app/platform/registry-api
pip3 install --user -r requirements.txt

# Run migration
export DATABASE_URL="postgresql://kristi@solvigo.ai@10.39.0.3:5432/registry"
alembic upgrade head
```

**Option 2: Cloud Build** (Automated):
```yaml
steps:
  - name: 'python:3.11'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        pip install -r requirements.txt
        cd platform/registry-api
        alembic upgrade head
```

**Option 3: Temporarily enable public IP** (Like we just did):
```bash
# Enable
gcloud sql instances patch solvigo-registry --assign-ip

# Run migration
alembic upgrade head

# Disable
gcloud sql instances patch solvigo-registry --no-assign-ip
```

### For Queries

**From Cloud Shell**:
```bash
psql "host=10.39.0.3 dbname=registry user=kristi@solvigo.ai"
```

**From local** (requires Cloud SQL Proxy with private IP support or temp public IP)

---

## Sample Queries

```sql
-- List all clients
SELECT * FROM clients;

-- List all projects with client info
SELECT
  c.name as client,
  p.name as project,
  p.full_domain,
  p.gcp_project_id,
  p.status
FROM projects p
JOIN clients c ON p.client_id = c.id
ORDER BY c.name, p.name;

-- Get all services for a project
SELECT
  s.name,
  s.type,
  e.name as environment,
  s.cloud_run_service,
  s.status
FROM services s
JOIN environments e ON s.environment_id = e.id
WHERE s.project_id = 'some-project-id';
```

---

## Next Steps

### Immediate
1. **Registry API** - Build FastAPI application to expose these tables
2. **CLI Integration** - Have CLI register projects in database
3. **Load Balancer Integration** - Query subdomain_mappings for routing

### Future
1. **Dashboard** - Web UI to view all projects
2. **Cost Import** - Automated cost allocation from GCP billing
3. **Monitoring** - Track service health
4. **Alerts** - Notify on deployment failures

---

## Connection Details

**Instance Connection Name**: `solvigo-platform-prod:europe-north1:solvigo-registry`
**Private IP**: `10.39.0.3`
**Database**: `registry`
**Port**: `5432`

**IAM Users**:
- `kristi@solvigo.ai` (superuser)
- `registry-api@solvigo-platform-prod.iam` (API service account)

---

**Status**: ✅ **COMPLETE - Database ready for registry API!**

The foundation for the central registry is now in place! 🎉

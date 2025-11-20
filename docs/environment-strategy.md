# Environment Strategy: Staging + Prod (Same Project)

## Decision

**Use 2 environments (staging + prod) in the same GCP project** with separate database instances.

## Rationale

### Why Not 3 Environments (Dev + Staging + Prod)?
- ❌ **Cloud dev is redundant** - developers use local docker-compose
- ❌ **Extra cost** for rarely-used environment
- ❌ **More complexity** without clear benefit
- ✅ **Local dev is better** - faster, no cloud costs, easier debugging

### Why Same Project (Not Separate)?
- ✅ **Self-sufficient** - no billing/project creation needed
- ✅ **Consultants can do it** - no admin permissions required
- ✅ **Lower cost** - shared infrastructure
- ✅ **Easy migration** - can separate later when needed
- ✅ **Simpler IAM** - all in one project

### Why Separate Databases?
- ✅ **Data isolation** - staging data doesn't affect prod
- ✅ **Safe testing** - can test migrations on staging DB
- ✅ **Realistic** - staging closer to production setup
- ✅ **Low cost** - Cloud SQL instances are affordable

---

## Architecture

### Same GCP Project, Environment Suffixes

```
bluegaz-customer-support (GCP project)
├── Cloud Run Services:
│   ├── backend-staging          (auto-deploys on main)
│   ├── backend                  (or backend-prod, tag-based)
│   ├── frontend-staging
│   └── frontend                 (or frontend-prod)
│
├── Cloud SQL Databases:
│   ├── customer-support-db-staging    (separate instance)
│   └── customer-support-db            (production instance)
│
├── Storage Buckets:
│   ├── customer-support-staging
│   └── customer-support-prod
│
└── Secrets (shared or separate):
    ├── api-key-staging
    └── api-key-prod
```

---

## Development Workflow

### 1. Local Development
```bash
docker-compose up
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# Database: Local PostgreSQL
```

**Benefits**:
- ✅ Fast iteration
- ✅ No cloud costs
- ✅ Full debugging capabilities
- ✅ Offline work possible

### 2. Staging Deployment
```bash
git add .
git commit -m "Add new feature"
git push origin main
```

**Triggers**:
- ✅ Cloud Build automatically triggers
- ✅ Deploys to `-staging` services
- ✅ Uses staging database
- ✅ No approval needed

**URL**: `https://backend-staging.bluegaz.solvigo.ai`

### 3. Production Deployment
```bash
# Test on staging first
# Then tag for production
git tag v1.2.0
git push origin v1.2.0
```

**Triggers**:
- ✅ Cloud Build triggers on tag
- ✅ Requires manual approval
- ✅ Deploys to production services
- ✅ Uses production database

**URL**: `https://backend.bluegaz.solvigo.ai`

---

## Cloud Build Triggers

### Staging Trigger
```yaml
Name: bluegaz-customer-support-staging
Event: Push to main branch
Approval: Not required (auto-deploy)
Deploys to:
  - backend-staging
  - frontend-staging
Uses: customer-support-db-staging
```

### Production Trigger
```yaml
Name: bluegaz-customer-support-prod
Event: Push tag matching v*.*.*
Approval: Required
Deploys to:
  - backend (or backend-prod)
  - frontend (or frontend-prod)
Uses: customer-support-db
```

---

## Service Naming Convention

### Existing Projects (Import)
**Existing services** keep their current names:
- `backend` → **Production** (add staging: `backend-staging`)
- `customer-support-api` → **Production** (add staging: `customer-support-api-staging`)

### New Projects (Init)
**Explicit naming**:
- `{service}-staging`
- `{service}-prod`

---

## Database Strategy

### Cloud SQL

**Staging Instance**:
```hcl
module "database_staging" {
  source = "../../../../modules/database-cloudsql"

  instance_name = "${var.project_name}-db-staging"
  database_type = "postgresql"
  tier          = "db-f1-micro"  # Smaller for staging
  # ...
}
```

**Production Instance** (existing or new):
```hcl
module "database_prod" {
  source = "../../../../modules/database-cloudsql"

  instance_name = "${var.project_name}-db"
  database_type = "postgresql"
  tier          = "db-n1-standard-1"  # Larger for prod
  # ...
}
```

### Firestore

**Collections** with environment prefix:
- `staging-users`
- `staging-orders`
- `users` (production)
- `orders` (production)

Or use separate Firestore databases (if multi-database mode enabled).

---

## Cost Implications

### Same Project (Our Choice)
```
Cloud Run:
  - 2 services × 2 environments = 4 services
  - Pay-per-use (minimal staging costs)

Cloud SQL:
  - Staging: db-f1-micro (~$7/month)
  - Prod: db-n1-standard-1 (~$50/month)
  - Total: ~$57/month

Storage:
  - Minimal (pay per GB)

Total: ~$60-100/month per client project
```

### Separate Projects (Alternative)
```
3 Projects × Setup = More complexity
+ Billing setup per project
+ Potentially 3× the cost

Total: ~$200-300/month per client project
```

**Savings**: ~$100-200/month by using same project!

---

## Migration Path to Separate Projects

When a client grows and needs full isolation:

### Step 1: Create New Projects
```bash
# Create staging and prod projects
gcloud projects create bluegaz-customer-support-staging
gcloud projects create bluegaz-customer-support-prod
```

### Step 2: Update Terraform
```hcl
module "cicd" {
  # ...

  client_project_ids = {
    staging = "bluegaz-customer-support-staging"  # New
    prod    = "bluegaz-customer-support-prod"     # New
  }
}
```

### Step 3: Migrate Resources
- Export data from shared database
- Import to separate databases
- Update Cloud Run to point to new projects
- Switch DNS

**Effort**: 2-4 hours per project

---

## Implementation in CLI

### Current Behavior (After Changes)

```
Which environments do you want to set up?

Note: Local development uses docker-compose (not cloud deployment)

☑ Staging (auto-deploy on push to main)
☑ Prod (manual approval, tag-based)
```

Both checked by default.

### Generated Resources

**Cloud Run** (for fullstack):
```hcl
# Staging
module "backend_staging" {
  service_name = "backend-staging"
  # ...
}

module "frontend_staging" {
  service_name = "frontend-staging"
  # ...
}

# Production (existing)
module "backend_prod" {
  service_name = "backend"  # Keep existing name
  # ...
}
```

**Databases**:
```hcl
# Staging
module "db_staging" {
  instance_name = "customer-support-db-staging"
  tier = "db-f1-micro"  # Smaller/cheaper
}

# Production
module "db_prod" {
  instance_name = "customer-support-db"
  tier = "db-n1-standard-1"  # Production-grade
}
```

---

## Changes Made

### 1. CLI Defaults
**`cli/solvigo/ui/cicd_prompts.py`**:
- Removed "Dev" option
- Default: `["staging", "prod"]`
- Added note about local development

### 2. Terraform Module
**`platform/modules/cloud-build-pipeline/variables.tf`**:
- `environments` default: `["staging", "prod"]`
- `staging_branch_pattern`: `^main$` (was `^staging$`)
- `require_approval_staging`: `false` (was `true`)
- Removed `dev_branch_pattern` variable

**`platform/modules/cloud-build-pipeline/main.tf`**:
- Removed dev trigger resource
- Updated staging trigger: auto-deploy, no approval by default
- Added comments explaining the strategy

### 3. Documentation
- Updated all guides to reflect 2-environment strategy
- Explained rationale
- Documented migration path

---

## Benefits Summary

| Aspect | Our Approach | Separate Projects |
|--------|--------------|-------------------|
| Self-sufficient | ✅ Yes | ❌ No (needs admin) |
| Consultant-friendly | ✅ Yes | ❌ Complex |
| Cost | ✅ ~$60/month | ❌ ~$200/month |
| Isolation | ⚠️ Medium | ✅ High |
| Migration later | ✅ Easy | N/A |
| Setup time | ✅ 2 minutes | ❌ 30 minutes |

---

## Workflow Examples

### Consultant Imports Existing Project

```bash
solvigo import bluegaz-customer-support

# Resources found:
# - Cloud Run: backend (existing)
# - Cloud SQL: customer-support-db (existing)

# Setup CI/CD? Yes
# Environments: [x] Staging [x] Prod

# Generated:
# - backend-staging (new)
# - backend (prod, imported)
# - customer-support-db-staging (new)
# - customer-support-db (prod, imported)
```

### Push to Staging
```bash
git push origin main
# → Auto-deploys to backend-staging
# → Uses customer-support-db-staging
# → No approval needed
```

### Deploy to Production
```bash
git tag v1.0.0
git push origin v1.0.0
# → Requires approval in Cloud Build console
# → Deploys to backend (prod)
# → Uses customer-support-db (prod)
```

---

## Summary

**Strategy**: Staging + Prod in same project with separate databases

**Rationale**:
- Self-sufficient for consultants
- Lower cost
- Simpler setup
- Easy to migrate later if needed

**Trade-off**: Less isolation (acceptable for most clients)

**Migration**: Can separate projects later when client grows

---

**Status**: ✅ **Implemented in CLI and Terraform modules**

Ready to test! 🚀

# Reference Architecture: Registry-API Patterns

## Overview

The registry-api infrastructure we just built provides **proven patterns** that should be reused for all client projects. This document analyzes what we built and how to templatize it.

---

## What We Built (registry-api)

### Infrastructure Stack
```
Cloud Run Service (registry-api)
  ↓ via VPC Connector
Cloud SQL PostgreSQL (private IP)
  ↓ within
Shared VPC Network
```

**Key Features**:
- ✅ Private database (no internet exposure)
- ✅ IAM authentication (no passwords)
- ✅ Service account with least privilege
- ✅ VPC connector for private access
- ✅ Automated deployment via Cloud Build
- ✅ All in Terraform state

---

## Reusable Patterns

### Pattern 1: Cloud Run + Private Cloud SQL

**What**: Backend service that needs a database

**Components**:
1. **Cloud SQL instance** (private IP)
2. **VPC connector** (Cloud Run → VPC)
3. **Service account** (for Cloud Run)
4. **IAM database user** (passwordless auth)
5. **Cloud Run service** (with DB connection)

**Example from registry-api**:

**Database** (`platform/terraform/registry-database/main.tf`):
```hcl
resource "google_sql_database_instance" "db" {
  name             = "my-db"
  database_version = "POSTGRES_15"
  region           = "europe-north1"

  settings {
    tier = "db-f1-micro"

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }

    ip_configuration {
      ipv4_enabled    = false  # Private only
      private_network = var.vpc_network_id
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }
  }
}

resource "google_sql_database" "db" {
  name     = "myapp"
  instance = google_sql_database_instance.db.name
}
```

**Service Account**:
```hcl
module "backend_sa" {
  source = "../../../modules/service-account"

  account_id   = "myapp-backend"
  display_name = "My App Backend"
  project_id   = var.project_id

  project_roles = [
    "roles/cloudsql.client"
  ]
}

resource "google_sql_user" "backend_sa" {
  instance = google_sql_database_instance.db.name
  name     = "${module.backend_sa.email}"  # Without .gserviceaccount.com
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}
```

**Cloud Run Service**:
```hcl
resource "google_cloud_run_service" "backend" {
  name     = "myapp-backend"
  location = "europe-north1"

  template {
    spec {
      service_account_name = module.backend_sa.email

      containers {
        image = var.image

        env {
          name  = "INSTANCE_CONNECTION_NAME"
          value = google_sql_database_instance.db.connection_name
        }
        env {
          name  = "DB_USER"
          value = "${module.backend_sa.email}"
        }
        env {
          name  = "DB_NAME"
          value = google_sql_database.db.name
        }
      }
    }

    metadata {
      annotations = {
        "run.googleapis.com/cloudsql-instances" = google_sql_database_instance.db.connection_name
        "run.googleapis.com/vpc-access-connector" = var.vpc_connector_id
        "run.googleapis.com/vpc-access-egress"    = "private-ranges-only"
      }
    }
  }
}
```

**Application Code** (Python with Cloud SQL Connector):
```python
from google.cloud.sql.connector import Connector
from sqlalchemy import create_engine

INSTANCE_CONNECTION_NAME = os.getenv('INSTANCE_CONNECTION_NAME')
DB_USER = os.getenv('DB_USER')
DB_NAME = os.getenv('DB_NAME')

connector = Connector()

def getconn():
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pg8000",
        user=DB_USER,
        db=DB_NAME,
        enable_iam_auth=True,
        ip_type="PRIVATE",
    )
    return conn

engine = create_engine("postgresql+pg8000://", creator=getconn)
```

---

### Pattern 2: VPC Connector (Shared)

**What**: Allow Cloud Run services to access private VPC resources

**When**: Needed once per region, shared by all Cloud Run services

**Terraform** (`platform/terraform/vpc-connector/`):
```hcl
resource "google_compute_subnetwork" "vpc_connector_subnet" {
  name          = "vpc-connector-subnet"
  ip_cidr_range = "10.8.0.0/28"  # /28 required (16 IPs)
  network       = var.vpc_network_id
}

resource "google_vpc_access_connector" "connector" {
  name          = "solvigo-vpc-connector"
  region        = "europe-north1"
  machine_type  = "e2-micro"
  min_instances = 2
  max_instances = 3

  subnet {
    name = google_compute_subnetwork.vpc_connector_subnet.name
  }
}
```

**Reuse**: All client Cloud Run services use the **same VPC connector**

---

### Pattern 3: Service Account with Database Access

**What**: Service account for Cloud Run service to access Cloud SQL

**Terraform**:
```hcl
# 1. Create service account
module "sa" {
  source = "../../../modules/service-account"

  account_id   = "myapp-backend"
  display_name = "My App Backend"
  project_id   = var.project_id

  project_roles = [
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",  # If using secrets
  ]
}

# 2. Grant database access (IAM auth)
resource "google_sql_user" "sa_db_user" {
  instance = var.db_instance_name
  name     = "myapp-backend@project-id.iam"  # Without .gserviceaccount.com
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}

# 3. Use in Cloud Run
resource "google_cloud_run_service" "app" {
  template {
    spec {
      service_account_name = module.sa.email
      # ...
    }
  }
}
```

---

### Pattern 4: Cloud Build Deployment

**What**: Automated deployment from GitHub

**Terraform** (already have this!):
```hcl
module "cicd" {
  source = "../../../../platform/modules/cloud-build-pipeline"

  github_connection_id = var.github_connection_id
  # ...
}
```

**Application**: `cloudbuild.yaml`
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '$_ARTIFACT_REPO/$_SERVICE_NAME:$SHORT_SHA', '.']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '$_ARTIFACT_REPO/$_SERVICE_NAME:$SHORT_SHA']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'run'
      - 'deploy'
      - '$_SERVICE_NAME'
      - '--image=$_ARTIFACT_REPO/$_SERVICE_NAME:$SHORT_SHA'
      - '--add-cloudsql-instances=$_DB_INSTANCE'
      - '--vpc-connector=solvigo-vpc-connector'
      - '--service-account=$_SERVICE_ACCOUNT'
```

---

### Pattern 5: Alembic Database Migrations

**What**: Version-controlled database schema changes

**Structure**:
```
app/
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py
│   ├── env.py
│   └── alembic.ini
```

**Migration File**:
```python
def upgrade():
    op.create_table('mytable', ...)
    op.create_index(...)

    # Grant permissions
    op.execute("""
        GRANT ALL ON ALL TABLES TO "myapp-backend@project.iam";
    """)

def downgrade():
    op.drop_table('mytable')
```

**Run Migration** (from Cloud Shell or with temp public IP):
```bash
export DATABASE_URL="postgresql://sa@host/db"
alembic upgrade head
```

---

## What Should Be Templated

### 1. Update `modules/cloud-run-app/`

**Add support for**:
- Database connection (Cloud SQL)
- VPC connector reference
- Service account with DB access
- Environment variables for DB connection

**Current** (simplified):
```hcl
resource "google_cloud_run_service" "service" {
  name = var.service_name
  # Basic configuration
}
```

**Enhanced** (with DB support):
```hcl
resource "google_cloud_run_service" "service" {
  name = var.service_name

  template {
    spec {
      service_account_name = var.service_account_email

      containers {
        image = var.image

        # Database connection env vars (if database is configured)
        dynamic "env" {
          for_each = var.database_instance != null ? [1] : []
          content {
            name  = "INSTANCE_CONNECTION_NAME"
            value = var.database_instance
          }
        }

        dynamic "env" {
          for_each = var.database_instance != null ? [1] : []
          content {
            name  = "DB_USER"
            value = var.service_account_email
          }
        }

        dynamic "env" {
          for_each = var.database_name != null ? [1] : []
          content {
            name  = "DB_NAME"
            value = var.database_name
          }
        }
      }
    }

    metadata {
      annotations = {
        # Cloud SQL connection
        "run.googleapis.com/cloudsql-instances" = var.database_instance != null ? var.database_instance : ""

        # VPC connector (for private DB access)
        "run.googleapis.com/vpc-access-connector" = var.vpc_connector
        "run.googleapis.com/vpc-access-egress"    = "private-ranges-only"
      }
    }
  }
}
```

### 2. Create `modules/cloud-run-with-database/`

**Purpose**: Opinionated module for Cloud Run + Cloud SQL pattern

**What it creates**:
- Service account
- IAM database user
- Cloud Run service with DB connection
- Proper environment variables

**Usage**:
```hcl
module "backend" {
  source = "../../../../modules/cloud-run-with-database"

  service_name      = "myapp-backend"
  image             = var.image
  database_instance = module.database.instance_connection_name
  database_name     = "myapp"
  vpc_connector     = "solvigo-vpc-connector"

  # Module creates:
  # 1. Service account
  # 2. IAM DB user
  # 3. Cloud Run service
  # All connected properly!
}
```

### 3. Update Database Modules

**Add to `modules/database-cloudsql/`**:
- Always enable IAM authentication
- Always use private IP
- Output IAM user creation helper

**Enhanced output**:
```hcl
output "iam_user_name" {
  description = "Name to use when creating IAM database user (without .gserviceaccount.com)"
  value       = "${var.instance_name}@${var.project_id}.iam"
}
```

### 4. Application Code Templates

**Create**: `cli/solvigo/templates/backend/database.py`

**Python template** (Jinja2):
```python
"""Database connection using Cloud SQL Connector with IAM auth"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from google.cloud.sql.connector import Connector

INSTANCE_CONNECTION_NAME = os.getenv('INSTANCE_CONNECTION_NAME')
DB_USER = os.getenv('DB_USER')
DB_NAME = os.getenv('DB_NAME')

connector = Connector()

def getconn():
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pg8000",
        user=DB_USER,
        db=DB_NAME,
        enable_iam_auth=True,
        ip_type="PRIVATE",
    )
    return conn

engine = create_engine("postgresql+pg8000://", creator=getconn)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## Comparison: Registry-API vs Client Project

### Registry-API (What We Built)

**Purpose**: Platform service (registry database)

**Infrastructure**:
```
Terraform:
  - platform/terraform/registry-database/
      - Cloud SQL instance
      - Database
      - IAM users
  - platform/terraform/vpc-connector/
      - VPC connector (shared)

Application:
  - platform/registry-api/
      - FastAPI code
      - Alembic migrations
      - Dockerfile
```

**Deployment**:
- Manual: `gcloud builds submit`
- Future: CI/CD trigger

### Client Project (Template)

**Purpose**: Client application (e.g., customer support backend)

**Infrastructure** (Generated by CLI):
```
Client Repo:
  terraform/
    - main.tf
    - database.tf          # Uses modules/database-cloudsql
    - cloud-run.tf         # Uses modules/cloud-run-with-database (NEW!)
    - cicd.tf              # Uses platform/modules/cloud-build-pipeline
    - service-account.tf   # Uses modules/service-account
```

**Pattern to use**:
```hcl
# Database
module "database_staging" {
  source = "../../../../modules/database-cloudsql"

  instance_name = "${var.project_name}-db-staging"
  database_type = "postgresql"
  tier          = "db-f1-micro"
  # Private IP, IAM auth enabled automatically
}

# Service account
module "backend_sa" {
  source = "../../../../modules/service-account"

  account_id   = "${var.project_name}-backend"
  project_id   = var.project_id
  project_roles = ["roles/cloudsql.client"]
}

# IAM database user
resource "google_sql_user" "backend_sa" {
  instance = module.database_staging.instance_name
  name     = "${var.project_name}-backend@${var.project_id}.iam"
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}

# Cloud Run with database
module "backend" {
  source = "../../../../modules/cloud-run-with-database"

  service_name      = "${var.project_name}-backend-staging"
  image             = var.backend_image
  service_account   = module.backend_sa.email
  database_instance = module.database_staging.instance_connection_name
  database_name     = module.database_staging.database_name
  vpc_connector     = "solvigo-vpc-connector"  # Shared platform connector
}
```

---

## Key Lessons from Registry-API

### 1. VPC Connector is Shared ✅
**Lesson**: Don't create VPC connector per project!

**Correct**:
- Platform has ONE VPC connector per region
- All client Cloud Run services use it
- Saves cost (~$8/month vs $8 × N projects)

**Template**: Client projects reference existing connector:
```hcl
vpc_connector = "solvigo-vpc-connector"  # Platform-provided
```

### 2. Private IP Databases Always ✅
**Lesson**: Never use public IP for databases

**Implementation**:
- `ipv4_enabled = false` always
- `private_network = var.vpc_network_id` always
- Access via VPC connector or Cloud Shell

**Template**: Our `database-cloudsql` module should default to private IP

### 3. IAM Authentication is Better ✅
**Lesson**: No passwords, use IAM

**Implementation**:
```hcl
database_flags {
  name  = "cloudsql.iam_authentication"
  value = "on"
}
```

**Template**: Enable by default in database module

### 4. Service Accounts Need Two Things ✅
**Lesson**: SA needs both project role AND database user

**Implementation**:
1. Project-level role: `roles/cloudsql.client`
2. Database-level user: IAM type

**Template**: Our modules should create both

### 5. Environment Variables Pattern ✅
**Lesson**: Use these env vars for DB connection

**Standard env vars**:
- `INSTANCE_CONNECTION_NAME` - Cloud SQL connection name
- `DB_USER` - Service account email (for IAM auth)
- `DB_NAME` - Database name

**Template**: CLI should generate these in cloudbuild.yaml

### 6. Cloud SQL Connector in Code ✅
**Lesson**: Use Cloud SQL Python Connector library

**Template**: Provide `database.py` template for backends:
```python
from google.cloud.sql.connector import Connector

connector = Connector()

def getconn():
    return connector.connect(
        os.getenv('INSTANCE_CONNECTION_NAME'),
        "pg8000",
        user=os.getenv('DB_USER'),
        db=os.getenv('DB_NAME'),
        enable_iam_auth=True,
        ip_type="PRIVATE",
    )

engine = create_engine("postgresql+pg8000://", creator=getconn)
```

---

## Action Items: Update Our Modules

### 1. Enhance `modules/database-cloudsql/`

**Add**:
- Default to private IP
- Always enable IAM auth
- Output IAM user name format

**New outputs**:
```hcl
output "iam_user_name" {
  value = "${var.instance_name}@${var.project_id}.iam"
}

output "instance_connection_name" {
  value = google_sql_database_instance.instance.connection_name
}

output "database_name" {
  value = google_sql_database.database.name
}
```

### 2. Enhance `modules/cloud-run-app/`

**Add variables**:
```hcl
variable "database_instance" {
  description = "Cloud SQL instance connection name (optional)"
  type        = string
  default     = null
}

variable "database_name" {
  description = "Database name (optional)"
  type        = string
  default     = null
}

variable "vpc_connector" {
  description = "VPC connector name"
  type        = string
  default     = "solvigo-vpc-connector"
}
```

**Add to service**:
- Cloud SQL connection annotation
- VPC connector annotation
- DB environment variables

### 3. Create `modules/cloud-run-with-database/` (NEW!)

**Purpose**: One module that creates everything for backend + DB pattern

**Creates**:
- Service account
- IAM database user
- Cloud Run service with all DB configuration

**Simplifies client Terraform**:
```hcl
# Instead of 3 module calls, just 1:
module "backend_staging" {
  source = "../../../../modules/cloud-run-with-database"

  service_name      = "myapp-backend-staging"
  image             = var.backend_image
  database_instance = module.db_staging.instance_connection_name
  database_name     = "myapp"
}
```

### 4. Add Application Code Templates

**Create**: `cli/solvigo/templates/backend/`
- `database.py` - Cloud SQL connector setup
- `models.py` - SQLAlchemy models example
- `main.py` - FastAPI skeleton
- `requirements.txt` - With all necessary deps

**CLI generates these** when creating/importing backend projects

---

## Recommended Updates

### Priority 1: Enhance Existing Modules

**Update `modules/database-cloudsql/`**:
- Ensure private IP by default
- Enable IAM auth by default
- Better outputs for IAM users

**Update `modules/cloud-run-app/`**:
- Add database connection support
- Add VPC connector support
- Add DB env vars

**Effort**: 1-2 hours

### Priority 2: Create New Module

**Create `modules/cloud-run-with-database/`**:
- Opinionated module for common pattern
- Creates SA, DB user, Cloud Run all together
- Reduces boilerplate

**Effort**: 2-3 hours

### Priority 3: Add Code Templates

**Create application templates**:
- Backend with DB connection code
- Frontend with API client
- Docker-compose for local dev

**Effort**: 3-4 hours

---

## Summary

| Pattern | From Registry-API | For Client Projects |
|---------|-------------------|---------------------|
| Database | Private IP, IAM auth | ✅ Same pattern |
| VPC Connector | Created once, reused | ✅ Reference platform connector |
| Service Account | SA + IAM DB user | ✅ Same pattern |
| Cloud Run | DB connection via VPC | ✅ Same pattern |
| Deployment | Cloud Build | ✅ Already have module |
| Migrations | Alembic | ✅ Provide template |
| Application Code | FastAPI + SQLAlchemy | ✅ Provide template |

---

## Next Steps

1. **Test CLI registry integration** (now)
   - Import a project
   - Verify it registers in database

2. **Enhance modules** (soon)
   - Update cloud-run-app for DB support
   - Update database-cloudsql defaults

3. **Create templates** (later)
   - Backend code with DB connection
   - Alembic setup
   - FastAPI skeleton

Want me to test the CLI registry integration now, or start enhancing the modules?

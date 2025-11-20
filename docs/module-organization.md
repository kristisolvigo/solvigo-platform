# Module Organization Guide

This document explains how modules are organized in the Solvigo platform and when to use each type.

## Overview

Modules are separated into two categories based on **who manages them** and **what they're used for**:

```
create-app/
├── platform/modules/        # Platform infrastructure modules (Solvigo manages)
└── modules/                 # Client application modules (CLI generates)
```

## Platform Modules (`platform/modules/`)

### Purpose
Infrastructure that **Solvigo platform team manages** for the organization.

### Who Uses Them
- Platform team (when setting up platform infrastructure)
- Client projects (for CI/CD setup managed by platform)

### Where They're Called From
- `platform/terraform/*/` - Platform infrastructure
- `clients/{client}/{project}/terraform/cicd.tf` - Client CI/CD (managed by platform)

### Current Modules

#### `cloud-build-pipeline/`
**Purpose**: Sets up complete CI/CD for a client project

**What it creates**:
- Deployer service account (in platform project)
- Artifact Registry repository (in platform project)
- GitHub repository link
- Build triggers (dev, staging, prod)
- Cross-project IAM permissions

**Used by**: Client projects for CI/CD (platform-managed)

**Example**:
```hcl
# In clients/acme-corp/app1/terraform/cicd.tf
module "cicd" {
  source = "../../../../platform/modules/cloud-build-pipeline"

  client_name         = "ACME Corp"
  project_name        = "App1"
  platform_project_id = "solvigo-platform-prod"
  client_project_id   = "acme-corp-app1-prod"
  # ...
}
```

**Why in platform/modules/**:
- Platform team controls CI/CD infrastructure
- Centralized in platform project
- Not directly part of client's application

---

## Client Modules (`modules/`)

### Purpose
Application infrastructure that **clients deploy** for their applications.

### Who Uses Them
- CLI tool (generates Terraform code using these modules)
- Client projects (when they deploy their applications)

### Where They're Called From
- `clients/{client}/{project}/terraform/main.tf` - Application infrastructure
- `clients/{client}/{project}/terraform/database.tf` - Database resources
- `clients/{client}/{project}/terraform/storage.tf` - Storage resources

### Current Modules

#### `gcp-project/`
**Purpose**: Creates a new GCP project with proper folder structure and labeling

**Used by**: Platform and CLI (when creating new client projects)

**Example**:
```hcl
module "project" {
  source = "../../../../modules/gcp-project"

  client_name        = "ACME Corp"
  project_name       = "app1"
  environment        = "prod"
  folder_id          = var.folder_id
  billing_account_id = var.billing_account_id
}
```

#### `service-account/`
**Purpose**: Generic service account creation with IAM bindings

**Used by**: Both platform modules and client modules

**Example**:
```hcl
module "runtime_sa" {
  source = "../../../../modules/service-account"

  account_id   = "app1-backend"
  display_name = "App1 Backend Runtime SA"
  project_id   = "acme-corp-app1-prod"

  project_roles = [
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor"
  ]
}
```

**Why in modules/** (not platform/modules/):
- Used by both platform AND clients
- Generic/reusable for any SA need
- Not specific to platform infrastructure

#### `cloud-run-app/`
**Purpose**: Deploys a Cloud Run service

**Used by**: CLI (generates code for client applications)

**Example**:
```hcl
module "backend" {
  source = "../../../../modules/cloud-run-app"

  service_name = "app1-backend"
  image        = "europe-north1-docker.pkg.dev/.../backend:latest"
  region       = "europe-north1"
  # ...
}
```

#### `load-balancer-backend/`
**Purpose**: Registers Cloud Run service with the global load balancer

**Used by**: CLI (generates code for client applications)

**Example**:
```hcl
module "lb_backend" {
  source = "../../../../modules/load-balancer-backend"

  service_name     = "app1-backend"
  domain           = "app1.acme-corp.solvigo.ai"
  cloud_run_region = "europe-north1"
  # ...
}
```

#### `database-cloudsql/`
**Purpose**: Creates Cloud SQL database instance

**Used by**: CLI (generates code for client applications)

**Example**:
```hcl
module "database" {
  source = "../../../../modules/database-cloudsql"

  instance_name = "app1-db"
  database_type = "postgresql"
  region        = "europe-north1"
  # ...
}
```

#### `database-firestore/`
**Purpose**: Sets up Firestore database

**Used by**: CLI (generates code for client applications)

#### `storage-bucket/`
**Purpose**: Creates Cloud Storage bucket

**Used by**: CLI (generates code for client applications)

#### `terraform-state-bucket/`
**Purpose**: Creates Terraform state bucket

**Used by**: Platform setup and CLI (for new client projects)

---

## Decision Tree: Which Directory?

### Is this module used ONLY by platform infrastructure?
- **YES** → `platform/modules/`
- **NO** → Continue

### Is this module used by client applications (via CLI)?
- **YES** → `modules/`
- **NO** → Continue

### Is this module generic and used by both?
- **YES** → `modules/` (shared modules)

---

## Examples by Use Case

### Use Case 1: Client Deploys Their Application

**Scenario**: ACME Corp deploys their App1 backend

**Files**:
```
clients/acme-corp/app1/terraform/
├── main.tf              # Uses: modules/cloud-run-app/
├── database.tf          # Uses: modules/database-cloudsql/
├── storage.tf           # Uses: modules/storage-bucket/
└── cicd.tf              # Uses: platform/modules/cloud-build-pipeline/
```

**Why**:
- Application modules (`cloud-run-app`, `database-cloudsql`, `storage-bucket`) are in `modules/` because they're part of the client's application
- CI/CD module (`cloud-build-pipeline`) is in `platform/modules/` because platform manages it

### Use Case 2: Platform Sets Up Shared Infrastructure

**Scenario**: Platform team deploys shared VPC

**Files**:
```
platform/terraform/shared-vpc/
└── main.tf              # Direct Terraform (no module needed)
```

**Why**:
- Platform infrastructure doesn't necessarily need modules
- Could create `platform/modules/shared-vpc/` if it's reusable

### Use Case 3: CLI Generates Client Project

**Scenario**: `solvigo init` creates new project

**CLI generates**:
```hcl
# clients/{client}/{project}/terraform/main.tf
module "backend" {
  source = "../../../../modules/cloud-run-app/"  # ← Client module
  # ...
}

# clients/{client}/{project}/terraform/cicd.tf
module "cicd" {
  source = "../../../../platform/modules/cloud-build-pipeline/"  # ← Platform module
  # ...
}
```

**Why**:
- Backend is client's application → `modules/`
- CI/CD is platform-managed → `platform/modules/`

---

## Module Path Reference

From a client terraform directory (`clients/{client}/{project}/terraform/`):

### Platform Modules
```hcl
source = "../../../../platform/modules/cloud-build-pipeline"
```

### Client Modules
```hcl
source = "../../../../modules/cloud-run-app"
source = "../../../../modules/database-cloudsql"
source = "../../../../modules/service-account"
```

---

## Future Modules

### Candidates for `platform/modules/`
- `shared-vpc-attachment/` - Connects client projects to platform VPC
- `dns-zone-delegation/` - Creates client DNS zones under main zone
- `monitoring-dashboard/` - Platform-managed monitoring
- `cost-tracking/` - Platform-managed cost allocation

### Candidates for `modules/`
- `cdn-bucket/` - CDN-optimized storage bucket
- `pubsub-topic/` - Pub/Sub topic and subscriptions
- `cloud-tasks-queue/` - Cloud Tasks queue
- `cloud-scheduler-job/` - Cloud Scheduler job
- `secret-manager-secret/` - Secret Manager secret

---

## Quick Reference Table

| Module | Location | Used By | Purpose |
|--------|----------|---------|---------|
| `cloud-build-pipeline` | `platform/modules/` | Platform (for clients) | CI/CD setup |
| `gcp-project` | `modules/` | Platform & CLI | Project creation |
| `service-account` | `modules/` | Platform & CLI & Clients | Generic SA |
| `cloud-run-app` | `modules/` | CLI | Deploy Cloud Run |
| `load-balancer-backend` | `modules/` | CLI | Register with LB |
| `database-cloudsql` | `modules/` | CLI | Cloud SQL DB |
| `database-firestore` | `modules/` | CLI | Firestore DB |
| `storage-bucket` | `modules/` | CLI | GCS bucket |
| `terraform-state-bucket` | `modules/` | Platform & CLI | State storage |

---

## Best Practices

### 1. Module Naming
- Use lowercase with hyphens: `cloud-run-app`, not `CloudRunApp`
- Be descriptive: `database-cloudsql`, not `db`
- Include resource type: `storage-bucket`, not just `storage`

### 2. Module Structure
Every module should have:
```
module-name/
├── main.tf          # Resource definitions
├── variables.tf     # Input variables
├── outputs.tf       # Output values
└── README.md        # Documentation with examples
```

### 3. Documentation
Each README should include:
- Purpose and what it creates
- Usage examples
- Input/output tables
- Best practices

### 4. Version Control
- Tag module versions for stability
- Document breaking changes
- Maintain backwards compatibility when possible

### 5. Testing
- Test modules in isolation
- Validate with `terraform validate`
- Plan before applying
- Document test scenarios

---

## Migration Notes

If you have existing code using old paths:

### Before (all modules in one directory)
```hcl
module "cicd" {
  source = "../../../../modules/cloud-build-pipeline"
  # ...
}
```

### After (organized by type)
```hcl
module "cicd" {
  source = "../../../../platform/modules/cloud-build-pipeline"
  # ...
}
```

### Update Commands
```bash
# Find all references
grep -r "modules/cloud-build-pipeline" clients/

# Update (macOS)
find clients/ -name "*.tf" -exec sed -i '' 's|modules/cloud-build-pipeline|platform/modules/cloud-build-pipeline|g' {} +

# Update (Linux)
find clients/ -name "*.tf" -exec sed -i 's|modules/cloud-build-pipeline|platform/modules/cloud-build-pipeline|g' {} +
```

---

## Summary

**Simple Rule**:
- **Platform manages it?** → `platform/modules/`
- **Clients deploy it?** → `modules/`
- **Both use it?** → `modules/` (shared)

This organization makes it clear what's platform infrastructure vs. client applications, making the codebase easier to understand and maintain.

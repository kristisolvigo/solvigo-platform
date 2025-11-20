# Service Account Module

Reusable Terraform module for creating GCP service accounts with IAM bindings.

## Features

- ✅ Creates service account in specified project
- ✅ Grants project-level IAM roles
- ✅ Supports cross-project IAM bindings
- ✅ Input validation for account_id
- ✅ Outputs for easy reference in other modules

## Usage

### Basic Service Account

```hcl
module "backend_sa" {
  source = "../../../modules/service-account"

  account_id   = "my-app-backend"
  display_name = "My App Backend Service Account"
  description  = "Runtime SA for backend Cloud Run service"
  project_id   = "my-project-id"

  project_roles = [
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
  ]
}
```

### Cloud Build Deployer Service Account

```hcl
module "deployer_sa" {
  source = "../../../modules/service-account"

  account_id   = "acme-corp-app1-deployer"
  display_name = "ACME Corp App1 Deployer"
  description  = "Cloud Build service account for deploying App1"
  project_id   = "solvigo-platform-prod"  # Created in platform project

  project_roles = [
    "roles/iam.serviceAccountUser",  # Can act as other SAs
    "roles/artifactregistry.writer",  # Push images
  ]

  # Grant access to client project
  cross_project_bindings = {
    "deploy-to-prod" = {
      project_id = "acme-corp-app1-prod"
      role       = "roles/run.admin"
    }
    "deploy-to-dev" = {
      project_id = "acme-corp-app1-dev"
      role       = "roles/run.admin"
    }
  }
}
```

### Cloud Run Runtime Service Account

```hcl
module "runtime_sa" {
  source = "../../../modules/service-account"

  account_id   = "app1-runtime"
  display_name = "App1 Runtime Service Account"
  description  = "Runtime identity for App1 Cloud Run service"
  project_id   = "acme-corp-app1-prod"

  project_roles = [
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/storage.objectViewer",
  ]
}

# Use in Cloud Run service
resource "google_cloud_run_service" "app" {
  # ...
  template {
    spec {
      service_account_name = module.runtime_sa.email
    }
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| account_id | Service account ID (6-30 chars, lowercase, hyphens) | string | - | yes |
| display_name | Human-readable name | string | - | yes |
| description | Description of purpose | string | "" | no |
| project_id | Project where SA is created | string | - | yes |
| project_roles | IAM roles in the same project | list(string) | [] | no |
| cross_project_bindings | IAM bindings for other projects | map(object) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| email | Service account email (e.g., `sa-name@project.iam.gserviceaccount.com`) |
| name | Fully qualified name (e.g., `projects/my-project/serviceAccounts/sa-name@...`) |
| id | Service account ID (same as name) |
| unique_id | Numeric unique ID |
| member | IAM member string (e.g., `serviceAccount:sa-name@...`) |

## Common IAM Roles

### For Cloud Build Deployer SAs

```hcl
project_roles = [
  "roles/iam.serviceAccountUser",       # Act as other service accounts
  "roles/artifactregistry.writer",       # Push Docker images
]

cross_project_bindings = {
  "deploy-cloudrun" = {
    project_id = var.client_project_id
    role       = "roles/run.admin"
  }
  "access-secrets" = {
    project_id = var.client_project_id
    role       = "roles/secretmanager.secretAccessor"
  }
}
```

### For Cloud Run Runtime SAs

```hcl
project_roles = [
  "roles/cloudsql.client",                # Connect to Cloud SQL
  "roles/secretmanager.secretAccessor",   # Read secrets
  "roles/storage.objectViewer",           # Read from GCS
  "roles/pubsub.publisher",               # Publish to Pub/Sub
]
```

### For Backend Services

```hcl
project_roles = [
  "roles/datastore.user",           # Firestore access
  "roles/cloudsql.client",          # Cloud SQL access
  "roles/secretmanager.secretAccessor",
  "roles/cloudtrace.agent",         # Send traces
  "roles/logging.logWriter",        # Write logs
]
```

## Best Practices

1. **Least Privilege**: Only grant necessary roles
2. **Naming Convention**: `{client}-{project}-{purpose}` (e.g., `acme-app1-deployer`)
3. **No Keys**: Avoid creating keys; use Workload Identity or direct SA assignment
4. **Separate SAs**: Different SAs for build-time vs runtime
5. **Documentation**: Always include `description` explaining purpose

## Examples in This Repo

See usage in:
- `modules/cloud-build-pipeline/main.tf` - Deployer SA
- `modules/cloud-run-app/main.tf` - Runtime SA
- `clients/*/terraform/*.tf` - Client-specific SAs

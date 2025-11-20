# Cloud Run App Module

Terraform module for deploying Cloud Run services with VPC integration, secrets, and IAM.

## Features

- Deploys Cloud Run service with container image
- Creates service account (or uses existing)
- Integrates with Secret Manager
- VPC Access connector support (for Shared VPC)
- Environment variables
- Auto-scaling configuration
- IAM bindings

## Usage

### Basic Example

```hcl
module "backend" {
  source = "../../modules/cloud-run-app"

  project_id   = "acme-corp-app1-prod"
  service_name = "api"
  region       = "europe-north2"

  image = "gcr.io/acme-corp/api:latest"

  labels = {
    client      = "acme-corp"
    project     = "app1"
    environment = "prod"
  }
}
```

### With Secrets and Environment Variables

```hcl
module "backend" {
  source = "../../modules/cloud-run-app"

  project_id   = "acme-corp-app1-prod"
  service_name = "api"

  image = "gcr.io/acme-corp/api:latest"

  env_vars = {
    NODE_ENV = "production"
    API_PORT = "8080"
  }

  secrets = {
    DATABASE_URL = "database-url"
    API_KEY      = "stripe-api-key"
  }
}
```

### With VPC Connector

```hcl
module "backend" {
  source = "../../modules/cloud-run-app"

  project_id   = "acme-corp-app1-prod"
  service_name = "api"

  vpc_connector_name = "projects/solvigo-platform-prod/locations/europe-north2/connectors/solvigo-vpc-connector"
}
```

### Production Configuration

```hcl
module "backend" {
  source = "../../modules/cloud-run-app"

  project_id   = "acme-corp-app1-prod"
  service_name = "api"

  image          = "gcr.io/acme-corp/api:v1.0.0"
  cpu            = "2000m"  # 2 CPUs
  memory         = "1Gi"
  min_instances  = 1        # Always 1 instance running
  max_instances  = 100
  concurrency    = 80
  cpu_throttling = false    # Always allocated

  allow_unauthenticated = true
}
```

## Image Management with CI/CD

This module is designed to work seamlessly with CI/CD pipelines (Cloud Build). It uses a placeholder image for initial deployment, then lets CI/CD manage actual image deployments.

### How It Works

**1. Initial Terraform Deployment**:
```bash
terraform apply
# Deploys service with placeholder: gcr.io/cloudrun/hello
# Service is created and immediately accessible (returns "Hello World")
```

**2. CI/CD Deploys Real Image**:
```bash
git push origin main
# Cloud Build:
# - Builds your image: europe-north2-docker.pkg.dev/project/repo/app:abc123
# - Deploys: gcloud run deploy app --image=...
# - Service now runs your actual application
```

**3. Subsequent Terraform Runs** (No Drift):
```bash
terraform apply
# Output: No changes. Your infrastructure matches the configuration.
#
# Image changes are ignored via lifecycle block - Terraform manages
# infrastructure (IAM, scaling, env vars), CI/CD manages deployments
```

### Why This Pattern?

**Separation of Concerns**:
- ✅ **Terraform**: Manages infrastructure (service config, IAM, scaling, env vars)
- ✅ **CI/CD**: Manages deployments (container images, versions)

**Benefits**:
- ✅ `terraform apply` succeeds immediately (placeholder works)
- ✅ No drift warnings after CI/CD deploys
- ✅ Clear ownership of image lifecycle
- ✅ Terraform state stays clean

**Implementation**:
The module uses `lifecycle.ignore_changes` to ignore image and auto-generated metadata, preventing Terraform from reverting CI/CD deployments.

### Manual Image Deployment

If you need to deploy a specific image version via Terraform (e.g., emergency rollback):

```hcl
module "backend" {
  source = "../../modules/cloud-run-app"

  image = "europe-north2-docker.pkg.dev/project/repo/app:v1.2.0"  # Specific version
  # ...
}
```

**Note**: With lifecycle.ignore_changes, Terraform will deploy this image on first apply but won't update it on subsequent applies. To force update, temporarily comment out the lifecycle block, apply, then re-enable it.

### Best Practice

For production:
1. Use Terraform for **initial service creation** and **infrastructure changes**
2. Use CI/CD (Cloud Build) for **routine deployments**
3. Use `image` variable for **emergency rollbacks** or **major version pins**

## Inputs

| Name | Description | Type | Default |
|------|-------------|------|---------|
| project_id | GCP Project ID | string | - |
| service_name | Cloud Run service name | string | - |
| region | GCP region | string | "europe-north2" |
| image | Container image URL | string | "gcr.io/cloudrun/hello" |
| env_vars | Environment variables | map(string) | {} |
| secrets | Secrets (env var → secret name) | map(string) | {} |
| cpu | CPU allocation | string | "1000m" |
| memory | Memory allocation | string | "512Mi" |
| port | Container port | number | 8080 |
| min_instances | Min instances (0 = scale to zero) | number | 0 |
| max_instances | Max instances | number | 10 |
| concurrency | Max concurrent requests/instance | number | 80 |
| timeout | Request timeout (seconds) | number | 300 |
| cpu_throttling | Enable CPU throttling | bool | true |
| allow_unauthenticated | Allow public access | bool | true |
| service_account_email | Service account (creates if empty) | string | "" |
| vpc_connector_name | VPC connector (empty to skip) | string | "" |
| labels | Resource labels | map(string) | {} |

## Outputs

| Name | Description |
|------|-------------|
| service_name | Cloud Run service name |
| service_url | Public URL |
| service_id | Service ID |
| service_location | Deployment region |
| service_account_email | Service account email |
| latest_revision | Latest revision name |

## Import Existing Service

```hcl
import {
  to = module.backend.google_cloud_run_service.service
  id = "locations/europe-north2/namespaces/PROJECT_ID/services/SERVICE_NAME"
}
```

## Notes

- Service account created automatically if not provided
- Secrets must exist before deploying
- VPC connector must exist if specified
- Default image is a hello world (replace with your image)

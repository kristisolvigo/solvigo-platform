# GCP Project Module

This Terraform module creates a GCP project with proper labeling, API enablement, and optional Shared VPC attachment.

## Features

- Creates GCP project in specified folder
- Applies mandatory labels for cost tracking (client, project, environment)
- Enables required GCP APIs
- Optionally attaches to Shared VPC as service project
- Configures IAM permissions for Shared VPC access
- Validates naming conventions and formats

## Usage

### Separate Projects Per Environment (Pattern A)

```hcl
# Production project
module "project_prod" {
  source = "../../modules/gcp-project"

  client_name        = "acme-corp"
  project_name       = "app1"
  environment        = "prod"
  folder_id          = "folders/123456789"
  billing_account_id = "ABCDEF-123456-GHIJKL"
}

# Development project
module "project_dev" {
  source = "../../modules/gcp-project"

  client_name        = "acme-corp"
  project_name       = "app1"
  environment        = "dev"
  folder_id          = "folders/123456789"
  billing_account_id = "ABCDEF-123456-GHIJKL"
}
```

This creates:
- `acme-corp-app1-prod`
- `acme-corp-app1-dev`

### Single Project (Pattern B)

```hcl
module "project" {
  source = "../../modules/gcp-project"

  client_name        = "techstart"
  project_name       = "api"
  environment        = ""  # Empty for single-project mode
  folder_id          = "folders/987654321"
  billing_account_id = "ABCDEF-123456-GHIJKL"
}
```

This creates:
- `techstart-api`

### With Additional APIs and Labels

```hcl
module "project" {
  source = "../../modules/gcp-project"

  client_name        = "acme-corp"
  project_name       = "ml-platform"
  environment        = "prod"
  folder_id          = "folders/123456789"
  billing_account_id = "ABCDEF-123456-GHIJKL"

  enabled_apis = [
    "compute.googleapis.com",
    "run.googleapis.com",
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
    "storage.googleapis.com",
  ]

  additional_labels = {
    team        = "data-science"
    compliance  = "sox"
  }
}
```

### Without Shared VPC

```hcl
module "project" {
  source = "../../modules/gcp-project"

  client_name        = "isolated-client"
  project_name       = "standalone-app"
  environment        = "prod"
  folder_id          = "folders/123456789"
  billing_account_id = "ABCDEF-123456-GHIJKL"

  attach_to_shared_vpc = false
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| client_name | Client name (lowercase, hyphens) | string | - | yes |
| project_name | Project name (lowercase, hyphens) | string | - | yes |
| environment | Environment (dev/staging/prod or empty) | string | "" | no |
| folder_id | GCP Folder ID (format: folders/123456789) | string | - | yes |
| billing_account_id | Billing Account ID (format: XXXXXX-XXXXXX-XXXXXX) | string | - | yes |
| enabled_apis | List of GCP APIs to enable | list(string) | See variables.tf | no |
| attach_to_shared_vpc | Attach to Shared VPC | bool | true | no |
| shared_vpc_host_project | Shared VPC host project ID | string | "solvigo-platform-prod" | no |
| additional_labels | Additional labels | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| project_id | GCP Project ID |
| project_number | GCP Project Number |
| project_name | GCP Project Name |
| labels | Applied labels |
| default_compute_sa | Default Compute service account email |
| cloud_run_sa | Cloud Run service agent email |
| enabled_services | List of enabled services |

## Labels

All projects get these mandatory labels:
- `client` - Client name
- `project` - Project name
- `environment` - Environment (or "multi-env" if single-project)
- `managed_by` - Always "terraform"
- `cost_center` - Always "client-billable"

## Naming Convention

**Pattern A (separate environments):**
`{client-name}-{project-name}-{environment}`

Examples:
- `acme-corp-app1-prod`
- `acme-corp-app1-dev`
- `techstart-dashboard-staging`

**Pattern B (single project):**
`{client-name}-{project-name}`

Examples:
- `techstart-api`
- `startup-xyz-web`

## IAM Permissions Configured

When `attach_to_shared_vpc = true`:
1. Default Compute SA gets `roles/compute.networkUser` on host project
2. Cloud Run SA gets `roles/vpcaccess.user` on host project

## Prerequisites

- GCP Organization with folders created
- Billing account with billing permissions
- Shared VPC host project (if using Shared VPC)
- Terraform >= 1.5.0

## Notes

- Projects are created with `auto_create_network = false`
- APIs are enabled with `disable_on_destroy = false` (safer)
- Naming follows strict validation (lowercase, hyphens only)
- Use empty `environment` for single-project mode

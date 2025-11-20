# Terraform State Bucket Module

Creates a GCS bucket for storing Terraform state with proper security and versioning.

## Features

- Uniform bucket-level access
- Versioning enabled (30 versions retained)
- Deletion protection
- IAM bindings for Terraform SA and admins
- Optional KMS encryption

## Usage

### Basic State Bucket

```hcl
module "client_state_bucket" {
  source = "../../modules/terraform-state-bucket"

  project_id   = "solvigo-platform-prod"
  bucket_name  = "acme-corp-terraform-state"
  location     = "europe-north2"

  terraform_sa_member = "serviceAccount:terraform@acme-corp.iam.gserviceaccount.com"

  labels = {
    client  = "acme-corp"
    purpose = "terraform-state"
  }
}
```

### With Admin Access

```hcl
module "client_state_bucket" {
  source = "../../modules/terraform-state-bucket"

  project_id   = "solvigo-platform-prod"
  bucket_name  = "acme-corp-terraform-state"

  terraform_sa_member = "serviceAccount:terraform@acme-corp.iam.gserviceaccount.com"

  admin_members = [
    "user:admin@solvigo.ai",
    "user:ceo@solvigo.ai"
  ]
}
```

## Inputs

| Name | Description | Type | Default |
|------|-------------|------|---------|
| project_id | GCP Project ID | string | - |
| bucket_name | Bucket name (must end with -terraform-state) | string | - |
| location | Bucket location | string | "europe-north2" |
| keep_versions | Number of versions to keep | number | 30 |
| kms_key_name | KMS key for encryption | string | null |
| terraform_sa_member | Terraform SA (objectAdmin) | string | - |
| admin_members | Admin users (objectViewer) | list(string) | null |
| labels | Resource labels | map(string) | {} |

## Outputs

| Name | Description |
|------|-------------|
| bucket_name | State bucket name |
| bucket_url | Bucket URL |
| versioning_enabled | Versioning status |

## Security

- **Uniform access:** Role-based IAM only
- **Versioning:** 30 versions retained for rollback
- **Force destroy:** Disabled (prevents accidental deletion)
- **Terraform SA:** objectAdmin (read/write state)
- **Admins:** objectViewer (read-only access)

# Storage Bucket Module

Terraform module for creating and managing Google Cloud Storage buckets.

## Features

- Creates GCS bucket with uniform access
- Optional versioning
- Lifecycle rules
- CORS configuration
- Proper labeling

## Usage

### Basic Bucket

```hcl
module "uploads" {
  source = "../../modules/storage-bucket"

  project_id  = "acme-corp-app1-prod"
  bucket_name = "acme-corp-app1-uploads"
  location    = "europe-north2"

  labels = {
    client  = "acme-corp"
    project = "app1"
    purpose = "uploads"
  }
}
```

### With Versioning

```hcl
module "backups" {
  source = "../../modules/storage-bucket"

  project_id  = "acme-corp-app1-prod"
  bucket_name = "acme-corp-app1-backups"

  enable_versioning = true
}
```

### With Lifecycle Rules

```hcl
module "logs" {
  source = "../../modules/storage-bucket"

  project_id  = "acme-corp-app1-prod"
  bucket_name = "acme-corp-app1-logs"

  lifecycle_rules = [
    {
      action             = "Delete"
      age                = 30
      num_newer_versions = 0
      with_state         = "ANY"
    }
  ]
}
```

## Inputs

| Name | Description | Type | Default |
|------|-------------|------|---------|
| project_id | GCP Project ID | string | - |
| bucket_name | Bucket name (globally unique) | string | - |
| location | Bucket location | string | "europe-north2" |
| enable_versioning | Enable object versioning | bool | false |
| force_destroy | Allow deletion if not empty | bool | false |
| lifecycle_rules | Object lifecycle rules | list(object) | [] |
| cors_origins | CORS allowed origins | list(string) | ["*"] |
| cors_methods | CORS allowed methods | list(string) | ["GET", "HEAD", ...] |
| labels | Resource labels | map(string) | {} |

## Outputs

| Name | Description |
|------|-------------|
| bucket_name | Bucket name |
| bucket_url | Bucket URL |
| bucket_self_link | Bucket self link |

## Import

```hcl
import {
  to = module.uploads.google_storage_bucket.bucket
  id = "bucket-name"
}
```

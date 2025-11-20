terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Terraform state bucket for client
resource "google_storage_bucket" "state_bucket" {
  name     = var.bucket_name
  location = var.location
  project  = var.project_id

  # Uniform bucket-level access (required for best practices)
  uniform_bucket_level_access = true

  # Never accidentally delete state!
  force_destroy = false

  # Enable versioning for state history
  versioning {
    enabled = true
  }

  # Lifecycle rules to manage old versions
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      num_newer_versions = var.keep_versions
      with_state         = "ARCHIVED"
    }
  }

  # Encryption
  encryption {
    default_kms_key_name = var.kms_key_name
  }

  labels = var.labels
}

# IAM binding for Terraform service account
resource "google_storage_bucket_iam_member" "terraform_access" {
  bucket = google_storage_bucket.state_bucket.name
  role   = "roles/storage.objectAdmin"
  member = var.terraform_sa_member
}

# IAM binding for admins (read-only recommended)
resource "google_storage_bucket_iam_member" "admin_access" {
  count = var.admin_members != null ? length(var.admin_members) : 0

  bucket = google_storage_bucket.state_bucket.name
  role   = "roles/storage.objectViewer"
  member = var.admin_members[count.index]
}

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

resource "google_storage_bucket" "bucket" {
  name     = var.bucket_name
  location = var.location
  project  = var.project_id

  uniform_bucket_level_access = true
  force_destroy               = var.force_destroy

  versioning {
    enabled = var.enable_versioning
  }

  dynamic "lifecycle_rule" {
    for_each = var.lifecycle_rules
    content {
      action {
        type = lifecycle_rule.value.action
      }
      condition {
        age                   = lifecycle_rule.value.age
        num_newer_versions    = lifecycle_rule.value.num_newer_versions
        with_state            = lifecycle_rule.value.with_state
      }
    }
  }

  cors {
    origin          = var.cors_origins
    method          = var.cors_methods
    response_header = ["*"]
    max_age_seconds = 3600
  }

  labels = var.labels
}

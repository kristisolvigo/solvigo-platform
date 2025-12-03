terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Cloud Run service
resource "google_cloud_run_service" "service" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    spec {
      service_account_name = var.service_account_email

      containers {
        image = var.image

        # Environment variables
        dynamic "env" {
          for_each = var.env_vars
          content {
            name  = env.key
            value = env.value
          }
        }

        # Secrets as environment variables
        dynamic "env" {
          for_each = var.secrets
          content {
            name = env.key
            value_from {
              secret_key_ref {
                name = env.value
                key  = "latest"
              }
            }
          }
        }

        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
          }
        }

        ports {
          container_port = var.port
        }
      }

      container_concurrency = var.max_instances > 0 ? var.concurrency : null
      timeout_seconds       = var.timeout
    }

    metadata {
      annotations = merge(
        {
          "autoscaling.knative.dev/minScale" = var.min_instances
          "autoscaling.knative.dev/maxScale" = var.max_instances
          "run.googleapis.com/cpu-throttling" = var.cpu_throttling ? "true" : "false"
        },
        var.vpc_connector_name != "" ? {
          "run.googleapis.com/vpc-access-connector" = var.vpc_connector_name
          "run.googleapis.com/vpc-access-egress"    = "all-traffic"
        } : {}
      )

      labels = var.labels
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true

  # Allow CI/CD to manage image deployments without Terraform drift warnings
  lifecycle {
    ignore_changes = [
      # CI/CD deploys images via Cloud Build - Terraform should not revert them
      template[0].spec[0].containers[0].image,

      # Auto-generated annotations by Cloud Run (ignore to prevent drift)
      template[0].metadata[0].annotations["run.googleapis.com/client-name"],
      template[0].metadata[0].annotations["run.googleapis.com/client-version"],
      template[0].metadata[0].annotations["client.knative.dev/user-image"],
      template[0].metadata[0].annotations["run.googleapis.com/operation-id"],

      # Auto-generated revision name (Terraform doesn't control this)
      template[0].metadata[0].name,
    ]
  }
}

# IAM binding for public access (if enabled)
resource "google_cloud_run_service_iam_member" "public_access" {
  count = var.allow_unauthenticated ? 1 : 0

  service  = google_cloud_run_service.service.name
  location = google_cloud_run_service.service.location
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Grant service account access to secrets
resource "google_secret_manager_secret_iam_member" "secret_access" {
  for_each = var.secrets

  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.service_account_email}"
}

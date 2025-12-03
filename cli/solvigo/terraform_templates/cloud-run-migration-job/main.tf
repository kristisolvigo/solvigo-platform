terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Cloud Run Job for database migrations
resource "google_cloud_run_v2_job" "migration_job" {
  name     = var.job_name
  location = var.region
  project  = var.project_id

  template {
    template {
      service_account = var.service_account_email

      containers {
        image = var.image  # Default to placeholder, CI/CD updates

        # Database connection
        env {
          name  = "DATABASE_URL"
          value = var.database_url
        }

        env {
          name  = "CLOUD_SQL_CONNECTION_NAME"
          value = var.cloud_sql_connection_name
        }

        # Migration-specific env vars
        dynamic "env" {
          for_each = var.env_vars
          content {
            name  = env.key
            value = env.value
          }
        }

        # Secrets (e.g., DB password if needed)
        dynamic "env" {
          for_each = var.secrets
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
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
      }

      # VPC connector for Cloud SQL access
      vpc_access {
        connector = var.vpc_connector_name
        egress    = "ALL_TRAFFIC"
      }

      timeout     = var.timeout
      max_retries = var.max_retries
    }
  }

  lifecycle {
    ignore_changes = [
      # CI/CD manages image deployments
      template[0].template[0].containers[0].image,
      # Auto-generated annotations
      template[0].annotations,
      template[0].labels,
    ]
  }

  labels = var.labels
}

# IAM binding to allow Cloud Build deployer to execute job
resource "google_cloud_run_v2_job_iam_member" "deployer_job_runner" {
  name     = google_cloud_run_v2_job.migration_job.name
  location = google_cloud_run_v2_job.migration_job.location
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.deployer_sa_email}"
}

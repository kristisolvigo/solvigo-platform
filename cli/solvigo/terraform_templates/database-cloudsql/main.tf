terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

# Random password for root user
resource "random_password" "root_password" {
  length  = 32
  special = true
}

# Cloud SQL instance
resource "google_sql_database_instance" "instance" {
  name             = var.instance_name
  database_version = var.database_version
  region           = var.region
  project          = var.project_id

  deletion_protection = var.deletion_protection

  settings {
    tier              = var.tier
    availability_type = var.high_availability ? "REGIONAL" : "ZONAL"
    disk_size         = var.disk_size
    disk_type         = var.disk_type
    disk_autoresize   = true

    backup_configuration {
      enabled            = var.enable_backups
      start_time         = "03:00"
      point_in_time_recovery_enabled = var.enable_backups
      backup_retention_settings {
        retained_backups = 7
      }
    }

    ip_configuration {
      ipv4_enabled                                  = var.public_ip
      private_network                               = var.private_network
      enable_private_path_for_google_cloud_services = var.private_network != null
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }

    database_flags {
      name  = "max_connections"
      value = var.max_connections
    }

    insights_config {
      query_insights_enabled  = true
      query_plans_per_minute  = 5
      query_string_length     = 1024
      record_application_tags = false
    }

    user_labels = var.labels
  }
}

# Create default database
resource "google_sql_database" "database" {
  name     = var.database_name
  instance = google_sql_database_instance.instance.name
  project  = var.project_id
}

# Store root password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.instance_name}-root-password"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels
}

resource "google_secret_manager_secret_version" "db_password_version" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.root_password.result
}

# Create root user
resource "google_sql_user" "root" {
  name     = "root"
  instance = google_sql_database_instance.instance.name
  password = random_password.root_password.result
  project  = var.project_id
}

# Create IAM user for application service account
# Note: For Cloud SQL IAM users, the name must NOT include .gserviceaccount.com suffix
resource "google_sql_user" "app_iam_user" {
  count = var.app_service_account_email != null ? 1 : 0

  name     = replace(var.app_service_account_email, ".gserviceaccount.com", "")
  instance = google_sql_database_instance.instance.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
  project  = var.project_id

  depends_on = [google_sql_database_instance.instance]
}

terraform {
  backend "gcs" {
    bucket = "solvigo-platform-terraform-state"
    prefix = "registry-database"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Get the VPC network
data "google_compute_network" "shared_vpc" {
  name    = "solvigo-shared-vpc"
  project = var.project_id
}

# Allocate IP range for private services (Cloud SQL)
resource "google_compute_global_address" "private_ip_range" {
  name          = "solvigo-private-services"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = data.google_compute_network.shared_vpc.id
  project       = var.project_id
}

# Create private VPC connection for Cloud SQL
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = data.google_compute_network.shared_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}

# Create Cloud SQL PostgreSQL instance for registry
resource "google_sql_database_instance" "registry" {
  name             = var.instance_name
  database_version = "POSTGRES_15"
  region           = var.region
  project          = var.project_id

  # Ensure VPC peering is set up before creating instance
  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-f1-micro"  # Smallest instance (~$7/month)

    # Enable deletion protection
    deletion_protection_enabled = true

    # Backup configuration
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"  # 3 AM
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
      }
    }

    # High availability (optional, adds cost)
    availability_type = "ZONAL"  # Use "REGIONAL" for HA

    # Database flags
    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }

    # IP configuration - private IP only (secure within VPC)
    ip_configuration {
      ipv4_enabled    = false  # No public IP (secure)
      private_network = data.google_compute_network.shared_vpc.id
      ssl_mode        = "ALLOW_UNENCRYPTED_AND_ENCRYPTED"
    }

    # Insights
    insights_config {
      query_insights_enabled  = true
      query_plans_per_minute  = 5
      query_string_length     = 1024
      record_application_tags = true
    }
  }

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true

    # Ignore settings changes since instance was created manually/imported
    ignore_changes = [
      settings
    ]
  }
}

# Create the registry database
resource "google_sql_database" "registry" {
  name     = "registry"
  instance = google_sql_database_instance.registry.name
  project  = var.project_id
}

# Grant kristi@solvigo.ai superadmin access (IAM authentication)
resource "google_sql_user" "kristi_admin" {
  instance = google_sql_database_instance.registry.name
  name     = "kristi@solvigo.ai"
  type     = "CLOUD_IAM_USER"
  project  = var.project_id
}

# Create service account for registry API
module "registry_api_sa" {
  source = "../../../modules/service-account"

  account_id   = "registry-api"
  display_name = "Solvigo Registry API"
  description  = "Service account for registry API to access database"
  project_id   = var.project_id

  project_roles = [
    "roles/cloudsql.client",  # Can connect to Cloud SQL
  ]
}

# Grant registry API service account database access (IAM authentication)
# Note: For IAM service accounts, use email without .gserviceaccount.com suffix
resource "google_sql_user" "registry_api" {
  instance = google_sql_database_instance.registry.name
  name     = "registry-api@solvigo-platform-prod.iam"  # Without .gserviceaccount.com suffix
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
  project  = var.project_id
}

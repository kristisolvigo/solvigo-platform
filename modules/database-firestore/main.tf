terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Firestore Database
resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = var.database_name
  location_id = var.location

  # Database type: FIRESTORE_NATIVE or DATASTORE_MODE
  type = var.database_type

  # Concurrency mode
  concurrency_mode = var.concurrency_mode

  # App Engine integration
  app_engine_integration_mode = var.app_engine_integration_mode

  # Point In Time Recovery (7-day retention)
  point_in_time_recovery_enablement = var.enable_pitr ? "POINT_IN_TIME_RECOVERY_ENABLED" : "POINT_IN_TIME_RECOVERY_DISABLED"

  # Deletion protection
  delete_protection_state = var.deletion_protection ? "DELETE_PROTECTION_ENABLED" : "DELETE_PROTECTION_DISABLED"
}

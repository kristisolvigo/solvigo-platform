terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Admin API Service Account
module "admin_api_sa" {
  source = "../modules/service-account"

  project_id   = var.project_id
  account_id   = "registry-api"  # Use existing service account name
  display_name = "Solvigo Admin API"
  description  = "Service account for Admin API to manage platform resources"

  # Platform project permissions
  project_roles = [
    "roles/iam.serviceAccountAdmin",        # Create deployer SAs
    "roles/compute.networkAdmin",           # Manage Shared VPC
    "roles/artifactregistry.admin",         # Manage registry permissions
    "roles/cloudbuild.builds.editor",       # Manage triggers
    "roles/cloudbuild.connectionViewer",    # View GitHub connections
    "roles/serviceusage.serviceUsageAdmin", # Enable APIs
    "roles/cloudsql.client",                # Connect to database
    "roles/cloudsql.instanceUser",          # IAM database authentication
  ]

  # Folder-level permissions (if using folders)
  folder_id = var.clients_folder_id
  folder_roles = var.clients_folder_id != null ? [
    "roles/resourcemanager.projectIamAdmin", # Grant roles on client projects
  ] : []
}

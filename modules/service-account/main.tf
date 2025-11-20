terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Create service account
resource "google_service_account" "sa" {
  account_id   = var.account_id
  display_name = var.display_name
  description  = var.description
  project      = var.project_id
}

# Grant project-level roles
resource "google_project_iam_member" "project_roles" {
  for_each = toset(var.project_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.sa.email}"
}

# Grant roles on other projects (e.g., deployer SA needs access to client projects)
resource "google_project_iam_member" "cross_project_roles" {
  for_each = var.cross_project_bindings

  project = each.value.project_id
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.sa.email}"
}

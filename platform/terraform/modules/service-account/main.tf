terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Service Account
resource "google_service_account" "sa" {
  account_id   = var.account_id
  display_name = var.display_name
  description  = var.description
  project      = var.project_id
}

# Project-level IAM bindings
resource "google_project_iam_member" "project_roles" {
  for_each = toset(var.project_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.sa.email}"
}

# Optional: Organization-level IAM bindings
resource "google_organization_iam_member" "org_roles" {
  for_each = var.organization_id != null ? toset(var.organization_roles) : []

  org_id = var.organization_id
  role   = each.value
  member = "serviceAccount:${google_service_account.sa.email}"
}

# Optional: Folder-level IAM bindings
resource "google_folder_iam_member" "folder_roles" {
  for_each = var.folder_id != null ? toset(var.folder_roles) : []

  folder = var.folder_id
  role   = each.value
  member = "serviceAccount:${google_service_account.sa.email}"
}

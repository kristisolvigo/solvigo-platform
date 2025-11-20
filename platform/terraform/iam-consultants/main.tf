terraform {
  backend "gcs" {
    bucket = "solvigo-platform-terraform-state"
    prefix = "iam-consultants"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  # No default project - working at folder/org level
}

# Grant folder management permissions at Solvigo folder level
# This allows consultants to create client folders and move projects

# Folder Admin - Create and manage folders
resource "google_folder_iam_member" "consultant_folder_admin" {
  for_each = toset(var.consultant_emails)

  folder = "folders/${var.solvigo_folder_id}"
  role   = "roles/resourcemanager.folderAdmin"
  member = "user:${each.value}"
}

# Project Mover - Move projects into folders
resource "google_folder_iam_member" "consultant_project_mover" {
  for_each = toset(var.consultant_emails)

  folder = "folders/${var.solvigo_folder_id}"
  role   = "roles/resourcemanager.projectMover"
  member = "user:${each.value}"
}

# Project Creator - Create new projects in folders (for init workflow)
resource "google_folder_iam_member" "consultant_project_creator" {
  for_each = toset(var.consultant_emails)

  folder = "folders/${var.solvigo_folder_id}"
  role   = "roles/resourcemanager.projectCreator"
  member = "user:${each.value}"
}

# Project Deleter - Delete/undelete projects (admin only)
resource "google_folder_iam_member" "admin_project_deleter" {
  for_each = toset(var.admin_emails)

  folder = "folders/${var.solvigo_folder_id}"
  role   = "roles/resourcemanager.projectDeleter"
  member = "user:${each.value}"
}

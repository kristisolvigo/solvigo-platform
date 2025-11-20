terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

locals {
  project_id = "${var.client_name}-${var.project_name}${var.environment != "" ? "-${var.environment}" : ""}"

  standard_labels = {
    client      = var.client_name
    project     = var.project_name
    environment = var.environment != "" ? var.environment : "multi-env"
    managed_by  = "terraform"
    cost_center = "client-billable"
  }

  labels = merge(local.standard_labels, var.additional_labels)
}

# Create GCP Project
resource "google_project" "project" {
  name            = local.project_id
  project_id      = local.project_id
  folder_id       = var.folder_id
  billing_account = var.billing_account_id
  labels          = local.labels

  auto_create_network = false
}

# Enable required APIs
resource "google_project_service" "services" {
  for_each = toset(var.enabled_apis)

  project = google_project.project.project_id
  service = each.key

  disable_on_destroy = false

  depends_on = [google_project.project]
}

# Attach to Shared VPC as Service Project
resource "google_compute_shared_vpc_service_project" "service" {
  count = var.attach_to_shared_vpc ? 1 : 0

  host_project    = var.shared_vpc_host_project
  service_project = google_project.project.project_id

  depends_on = [
    google_project_service.services
  ]
}

# Grant Shared VPC User role to default compute service account
resource "google_project_iam_member" "shared_vpc_user" {
  count = var.attach_to_shared_vpc ? 1 : 0

  project = var.shared_vpc_host_project
  role    = "roles/compute.networkUser"
  member  = "serviceAccount:${google_project.project.number}-compute@developer.gserviceaccount.com"

  depends_on = [
    google_project_service.services,
    google_compute_shared_vpc_service_project.service
  ]
}

# Grant Cloud Run Service Agent access to Shared VPC
resource "google_project_iam_member" "cloud_run_vpc_access" {
  count = var.attach_to_shared_vpc && contains(var.enabled_apis, "run.googleapis.com") ? 1 : 0

  project = var.shared_vpc_host_project
  role    = "roles/vpcaccess.user"
  member  = "serviceAccount:service-${google_project.project.number}@serverless-robot-prod.iam.gserviceaccount.com"

  depends_on = [
    google_project_service.services,
    google_compute_shared_vpc_service_project.service
  ]
}

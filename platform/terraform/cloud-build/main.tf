terraform {
  backend "gcs" {
    bucket = "solvigo-platform-terraform-state"
    prefix = "cloud-build"
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

# Reference GitHub connection created manually in GCP Console
#
# To create the connection:
# 1. Go to: https://console.cloud.google.com/cloud-build/triggers?project=solvigo-platform-prod
# 2. Click "Connect Repository" → "GitHub (Cloud Build GitHub App)"
# 3. Authenticate with GitHub and grant access to your org
# 4. Connection is created (default name: "solvigo-github")
#
# To import into Terraform (optional):
# terraform import google_cloudbuildv2_connection.github \
#   projects/solvigo-platform-prod/locations/europe-north1/connections/solvigo-github

resource "google_cloudbuildv2_connection" "github" {
  location = var.region
  name     = var.github_connection_name
  project  = var.project_id

  # Configuration is managed by console
  # No github_config block needed when importing existing connection

  lifecycle {
    # Prevent Terraform from trying to recreate if already exists
    prevent_destroy = true

    # Ignore changes to github_config - managed by console
    ignore_changes = [
      github_config,
      annotations,
      disabled
    ]
  }
}

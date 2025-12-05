# Enable required GCP APIs
# These must be enabled before creating Certificate Manager resources

resource "google_project_service" "certificate_manager" {
  project = var.project_id
  service = "certificatemanager.googleapis.com"

  disable_on_destroy = false
}

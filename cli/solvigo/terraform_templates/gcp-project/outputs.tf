output "project_id" {
  description = "GCP Project ID"
  value       = google_project.project.project_id
}

output "project_number" {
  description = "GCP Project Number"
  value       = google_project.project.number
}

output "project_name" {
  description = "GCP Project Name"
  value       = google_project.project.name
}

output "labels" {
  description = "Labels applied to project"
  value       = local.labels
}

output "default_compute_sa" {
  description = "Default Compute Engine service account email"
  value       = "${google_project.project.number}-compute@developer.gserviceaccount.com"
}

output "cloud_run_sa" {
  description = "Cloud Run service agent email"
  value       = "service-${google_project.project.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

output "enabled_services" {
  description = "List of enabled GCP services"
  value       = [for s in google_project_service.services : s.service]
}

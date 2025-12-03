output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_service.service.name
}

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_service.service.status[0].url
}

output "service_id" {
  description = "Cloud Run service ID"
  value       = google_cloud_run_service.service.id
}

output "service_location" {
  description = "Cloud Run service location"
  value       = google_cloud_run_service.service.location
}

output "service_account_email" {
  description = "Service account email used by Cloud Run"
  value       = var.service_account_email
}

output "latest_revision" {
  description = "Latest revision name"
  value       = google_cloud_run_service.service.status[0].latest_ready_revision_name
}

output "email" {
  description = "Service account email address"
  value       = google_service_account.sa.email
}

output "name" {
  description = "Service account fully qualified name"
  value       = google_service_account.sa.name
}

output "id" {
  description = "Service account ID (same as name)"
  value       = google_service_account.sa.id
}

output "unique_id" {
  description = "Unique numeric ID of the service account"
  value       = google_service_account.sa.unique_id
}

output "member" {
  description = "IAM member string (serviceAccount:email)"
  value       = "serviceAccount:${google_service_account.sa.email}"
}

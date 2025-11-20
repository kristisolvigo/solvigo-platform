output "bucket_name" {
  description = "State bucket name"
  value       = google_storage_bucket.state_bucket.name
}

output "bucket_url" {
  description = "State bucket URL"
  value       = google_storage_bucket.state_bucket.url
}

output "bucket_self_link" {
  description = "State bucket self link"
  value       = google_storage_bucket.state_bucket.self_link
}

output "versioning_enabled" {
  description = "Whether versioning is enabled"
  value       = google_storage_bucket.state_bucket.versioning[0].enabled
}

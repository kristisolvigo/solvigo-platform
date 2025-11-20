output "github_connection_id" {
  description = "GitHub connection ID (pass to client CI/CD modules)"
  value       = google_cloudbuildv2_connection.github.id
}

output "github_connection_name" {
  description = "GitHub connection name"
  value       = google_cloudbuildv2_connection.github.name
}

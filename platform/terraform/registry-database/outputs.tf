output "instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.registry.name
}

output "instance_connection_name" {
  description = "Cloud SQL instance connection name (for Cloud SQL Proxy)"
  value       = google_sql_database_instance.registry.connection_name
}

output "database_name" {
  description = "Database name"
  value       = google_sql_database.registry.name
}

output "private_ip_address" {
  description = "Private IP address"
  value       = google_sql_database_instance.registry.private_ip_address
}

output "registry_api_sa_email" {
  description = "Registry API service account email"
  value       = module.registry_api_sa.email
}

output "connection_string" {
  description = "Connection string for Alembic (use Cloud SQL Proxy)"
  value       = "postgresql://kristi@solvigo.ai@/${google_sql_database.registry.name}?host=/cloudsql/${google_sql_database_instance.registry.connection_name}"
  sensitive   = true
}

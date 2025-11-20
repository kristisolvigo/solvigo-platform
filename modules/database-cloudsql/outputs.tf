output "instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.instance.name
}

output "connection_name" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.instance.connection_name
}

output "database_name" {
  description = "Database name"
  value       = google_sql_database.database.name
}

output "password_secret_id" {
  description = "Secret Manager secret ID for root password"
  value       = google_secret_manager_secret.db_password.secret_id
}

output "private_ip" {
  description = "Private IP address"
  value       = google_sql_database_instance.instance.private_ip_address
}

output "public_ip" {
  description = "Public IP address"
  value       = google_sql_database_instance.instance.public_ip_address
}

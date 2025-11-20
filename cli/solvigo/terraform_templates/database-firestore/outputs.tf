output "database_name" {
  description = "Firestore database name"
  value       = google_firestore_database.database.name
}

output "database_id" {
  description = "Firestore database ID"
  value       = google_firestore_database.database.id
}

output "location" {
  description = "Database location"
  value       = google_firestore_database.database.location_id
}

output "database_type" {
  description = "Database type"
  value       = google_firestore_database.database.type
}

output "create_time" {
  description = "Database creation time"
  value       = google_firestore_database.database.create_time
}

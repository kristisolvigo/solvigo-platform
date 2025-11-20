output "connector_name" {
  description = "VPC connector name"
  value       = google_vpc_access_connector.solvigo_connector.name
}

output "connector_id" {
  description = "VPC connector ID"
  value       = google_vpc_access_connector.solvigo_connector.id
}

output "connector_self_link" {
  description = "VPC connector self link (use in Cloud Run)"
  value       = google_vpc_access_connector.solvigo_connector.self_link
}

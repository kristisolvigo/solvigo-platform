output "connector_north1_name" {
  description = "VPC connector name for europe-north1"
  value       = google_vpc_access_connector.solvigo_connector_north1.name
}

output "connector_north1_id" {
  description = "VPC connector ID for europe-north1"
  value       = google_vpc_access_connector.solvigo_connector_north1.id
}

output "connector_north2_name" {
  description = "VPC connector name for europe-north2"
  value       = google_vpc_access_connector.solvigo_connector_north2.name
}

output "connector_north2_id" {
  description = "VPC connector ID for europe-north2"
  value       = google_vpc_access_connector.solvigo_connector_north2.id
}

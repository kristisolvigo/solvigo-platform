output "neg_id" {
  description = "Network Endpoint Group ID"
  value       = google_compute_region_network_endpoint_group.neg.id
}

output "backend_service_id" {
  description = "Backend service ID"
  value       = google_compute_backend_service.backend.id
}

output "backend_service_name" {
  description = "Backend service name"
  value       = google_compute_backend_service.backend.name
}

output "dns_records" {
  description = "DNS A records created"
  value       = [for record in google_dns_record_set.service : record.name]
}

output "hostnames" {
  description = "Configured hostnames"
  value       = var.hostnames
}

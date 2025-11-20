output "network_id" {
  description = "Shared VPC network ID"
  value       = google_compute_network.shared_vpc.id
}

output "network_name" {
  description = "Shared VPC network name"
  value       = google_compute_network.shared_vpc.name
}

output "network_self_link" {
  description = "Shared VPC network self link"
  value       = google_compute_network.shared_vpc.self_link
}

output "subnet_ids" {
  description = "Map of subnet names to IDs"
  value = {
    for k, v in google_compute_subnetwork.subnets : k => v.id
  }
}

output "subnet_self_links" {
  description = "Map of subnet names to self links"
  value = {
    for k, v in google_compute_subnetwork.subnets : k => v.self_link
  }
}

output "router_ids" {
  description = "Map of region to router IDs"
  value = {
    for k, v in google_compute_router.router : k => v.id
  }
}

output "nat_ips" {
  description = "Map of region to NAT IP addresses (auto-allocated)"
  value = {
    for k, v in google_compute_router_nat.nat : k => v.name
  }
}

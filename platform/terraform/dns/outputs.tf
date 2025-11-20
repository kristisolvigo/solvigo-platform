output "main_zone_name" {
  description = "Main DNS zone name"
  value       = google_dns_managed_zone.main.name
}

output "main_zone_dns_name" {
  description = "Main DNS zone DNS name"
  value       = google_dns_managed_zone.main.dns_name
}

output "main_zone_name_servers" {
  description = "Main DNS zone name servers (configure these at your domain registrar)"
  value       = google_dns_managed_zone.main.name_servers
}

output "client_zones" {
  description = "Map of client zone names to their details"
  value = {
    for k, v in google_dns_managed_zone.client_zones : k => {
      zone_name    = v.name
      dns_name     = v.dns_name
      name_servers = v.name_servers
    }
  }
}

output "client_zone_names" {
  description = "Map of client names to zone names"
  value = {
    for k, v in google_dns_managed_zone.client_zones : k => v.name
  }
}

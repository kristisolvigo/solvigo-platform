output "load_balancer_ip" {
  description = "Global Load Balancer IP address"
  value       = google_compute_global_address.lb_ip.address
}

output "load_balancer_ip_name" {
  description = "Global Load Balancer IP address name"
  value       = google_compute_global_address.lb_ip.name
}

output "url_map_id" {
  description = "URL Map ID (for adding host rules)"
  value       = google_compute_url_map.lb.id
}

output "url_map_self_link" {
  description = "URL Map self link"
  value       = google_compute_url_map.lb.self_link
}

output "ssl_certificate_id" {
  description = "Managed SSL certificate ID"
  value       = var.enable_ssl ? google_compute_managed_ssl_certificate.lb[0].id : null
}

output "ssl_certificate_domains" {
  description = "Domains covered by SSL certificate"
  value       = var.enable_ssl ? google_compute_managed_ssl_certificate.lb[0].managed[0].domains : []
}

output "ssl_certificate_name" {
  description = "SSL certificate name (use with gcloud to check status)"
  value       = var.enable_ssl ? google_compute_managed_ssl_certificate.lb[0].name : null
}

output "check_ssl_status_command" {
  description = "Run this command to check SSL certificate status"
  value       = var.enable_ssl ? "gcloud compute ssl-certificates describe ${google_compute_managed_ssl_certificate.lb[0].name} --global --project=${var.project_id}" : null
}

output "https_forwarding_rule" {
  description = "HTTPS forwarding rule name"
  value       = var.enable_ssl ? google_compute_global_forwarding_rule.https[0].name : null
}

output "http_forwarding_rule" {
  description = "HTTP forwarding rule name"
  value       = google_compute_global_forwarding_rule.http.name
}

output "dns_configuration" {
  description = "DNS A record configuration needed"
  value = {
    domain     = var.domain
    ip_address = google_compute_global_address.lb_ip.address
    record_type = "A"
    note       = "Create A records for your domains pointing to this IP"
  }
}

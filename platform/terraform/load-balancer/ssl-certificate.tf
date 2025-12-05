# SSL Certificate Configuration using Certificate Manager
# Certificate Manager supports wildcard domains (*.solvigo.ai, *.*.solvigo.ai)
# Classic managed SSL certs do NOT support wildcards

# DNS Authorization for wildcard certificates
# One authorization for the base domain covers all wildcard levels
resource "google_certificate_manager_dns_authorization" "solvigo_dns_auth" {
  project     = var.project_id
  name        = "solvigo-dns-auth"
  description = "DNS authorization for wildcard SSL certificate"
  domain      = "solvigo.ai"

  depends_on = [google_project_service.certificate_manager]
}

# Wildcard SSL Certificate via Certificate Manager
# Covers solvigo.ai, *.solvigo.ai, and *.*.solvigo.ai
resource "google_certificate_manager_certificate" "solvigo_wildcard_cert" {
  project     = var.project_id
  name        = "solvigo-wildcard-cert"
  description = "Wildcard SSL certificate for all Solvigo domains"
  scope       = "DEFAULT"

  managed {
    domains = [
      "solvigo.ai",
      "*.solvigo.ai"
    ]

    dns_authorizations = [
      google_certificate_manager_dns_authorization.solvigo_dns_auth.id
    ]
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Certificate Map to attach certificates to load balancer
resource "google_certificate_manager_certificate_map" "solvigo_cert_map" {
  project     = var.project_id
  name        = "solvigo-cert-map"
  description = "Certificate map for Solvigo load balancer"

  depends_on = [google_project_service.certificate_manager]
}

# Certificate Map Entry - maps all domains to the wildcard certificate
resource "google_certificate_manager_certificate_map_entry" "solvigo_wildcard_entry" {
  project      = var.project_id
  name         = "solvigo-wildcard-entry"
  map          = google_certificate_manager_certificate_map.solvigo_cert_map.name
  certificates = [google_certificate_manager_certificate.solvigo_wildcard_cert.id]
  matcher      = "PRIMARY" # Catch-all matcher
}

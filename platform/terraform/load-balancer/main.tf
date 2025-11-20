provider "google" {
  project = var.project_id
}

locals {
  standard_labels = {
    managed_by  = "terraform"
    environment = "prod"
    cost_center = "internal"
    component   = "load-balancer"
  }
}

# Reserve static external IP address
resource "google_compute_global_address" "lb_ip" {
  name         = "solvigo-lb-ip"
  address_type = "EXTERNAL"
  project      = var.project_id
}

# Default backend service (returns 404 for unmatched routes)
resource "google_compute_backend_service" "default" {
  name        = "solvigo-lb-default-backend"
  protocol    = "HTTP"
  port_name   = "http"
  timeout_sec = 30
  project     = var.project_id

  # No backends - will return 404
  # Alternatively, you can create a Cloud Run service that returns a custom 404 page

  health_checks = [google_compute_health_check.default.id]

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

# Default health check
resource "google_compute_health_check" "default" {
  name               = "solvigo-lb-default-health-check"
  check_interval_sec = 10
  timeout_sec        = 5
  project            = var.project_id

  http_health_check {
    port         = 80
    request_path = "/"
  }
}

# URL Map (routing configuration)
resource "google_compute_url_map" "lb" {
  name            = "solvigo-lb-url-map"
  default_service = google_compute_backend_service.default.id
  project         = var.project_id

  # Host rules and path matchers will be added dynamically per client
  # This is a baseline configuration

  # Example host rule (commented out - will be added via separate resources per client)
  # host_rule {
  #   hosts        = ["*.acme-corp.solvigo.ai"]
  #   path_matcher = "acme-corp-matcher"
  # }
  #
  # path_matcher {
  #   name            = "acme-corp-matcher"
  #   default_service = google_compute_backend_service.default.id
  #
  #   path_rule {
  #     paths   = ["/*"]
  #     service = "backend-service-for-acme-corp"
  #   }
  # }
}

# HTTP(S) Proxy
resource "google_compute_target_https_proxy" "lb" {
  count = var.enable_ssl ? 1 : 0

  name    = "solvigo-lb-https-proxy"
  url_map = google_compute_url_map.lb.id
  project = var.project_id

  ssl_certificates = [google_compute_managed_ssl_certificate.lb[0].id]
}

resource "google_compute_target_http_proxy" "lb" {
  name    = "solvigo-lb-http-proxy"
  url_map = google_compute_url_map.lb.id
  project = var.project_id
}

# Managed SSL Certificate
resource "google_compute_managed_ssl_certificate" "lb" {
  count = var.enable_ssl ? 1 : 0

  name    = "solvigo-lb-ssl-cert"
  project = var.project_id

  managed {
    domains = var.ssl_domains
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Global Forwarding Rule (HTTPS)
resource "google_compute_global_forwarding_rule" "https" {
  count = var.enable_ssl ? 1 : 0

  name       = "solvigo-lb-https-forwarding-rule"
  target     = google_compute_target_https_proxy.lb[0].id
  port_range = "443"
  ip_address = google_compute_global_address.lb_ip.address
  project    = var.project_id

  labels = local.standard_labels
}

# Global Forwarding Rule (HTTP) - Redirect to HTTPS
resource "google_compute_global_forwarding_rule" "http" {
  name       = "solvigo-lb-http-forwarding-rule"
  target     = google_compute_target_http_proxy.lb.id
  port_range = "80"
  ip_address = google_compute_global_address.lb_ip.address
  project    = var.project_id

  labels = local.standard_labels
}

# HTTP to HTTPS redirect (optional - can be configured in URL map)
resource "google_compute_url_map" "http_redirect" {
  count = var.enable_ssl ? 1 : 0

  name    = "solvigo-lb-http-redirect"
  project = var.project_id

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

# Update HTTP proxy to use redirect URL map
resource "google_compute_target_http_proxy" "redirect" {
  count = var.enable_ssl ? 1 : 0

  name    = "solvigo-lb-http-redirect-proxy"
  url_map = google_compute_url_map.http_redirect[0].id
  project = var.project_id
}

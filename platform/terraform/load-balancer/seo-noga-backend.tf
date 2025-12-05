# SEO Text Optimization - Noga Client
# Backend configuration for noga-seo.solvigo.ai

# Serverless NEG for Cloud Run service
resource "google_compute_region_network_endpoint_group" "seo_noga_neg" {
  name                  = "seo-noga-frontend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = "europe-north2"
  project               = var.project_id

  cloud_run {
    service = "seo-frontend"
  }

  # Reference the service in the seo-text-optimization project
  # Note: The NEG is created in the platform project but points to a service in another project
}

# Backend service for SEO frontend
resource "google_compute_backend_service" "seo_noga_backend" {
  name        = "seo-noga-frontend-backend"
  protocol    = "HTTP"
  port_name   = "http"
  timeout_sec = 30
  project     = var.project_id

  backend {
    group = google_compute_region_network_endpoint_group.seo_noga_neg.id
  }

  # Enable CDN for better performance
  cdn_policy {
    cache_mode  = "CACHE_ALL_STATIC"
    default_ttl = 3600
    max_ttl     = 86400
    client_ttl  = 7200

    cache_key_policy {
      include_host         = true
      include_protocol     = true
      include_query_string = true
    }
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

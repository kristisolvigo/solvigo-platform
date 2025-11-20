terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Get the platform load balancer URL map
data "terraform_remote_state" "load_balancer" {
  backend = "gcs"
  config = {
    bucket = var.platform_state_bucket
    prefix = "load-balancer"
  }
}

# Create serverless NEG for Cloud Run
resource "google_compute_region_network_endpoint_group" "neg" {
  name                  = "${var.service_name}-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  project               = var.platform_project

  cloud_run {
    service = var.cloud_run_service_name
  }
}

# Create backend service
resource "google_compute_backend_service" "backend" {
  name        = "${var.client_name}-${var.service_name}-backend"
  protocol    = "HTTP"
  port_name   = "http"
  timeout_sec = 30
  project     = var.platform_project

  backend {
    group = google_compute_region_network_endpoint_group.neg.id
  }

  dynamic "cdn_policy" {
    for_each = var.enable_cdn ? [1] : []
    content {
      cache_mode  = "CACHE_ALL_STATIC"
      default_ttl = 3600
      max_ttl     = 86400
      client_ttl  = 7200
    }
  }

  dynamic "iap" {
    for_each = var.enable_iap ? [1] : []
    content {
      oauth2_client_id     = var.iap_client_id
      oauth2_client_secret = var.iap_client_secret
    }
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

# Note: URL map updates must be done manually or via separate resource
# This is because URL map is managed in platform/terraform/load-balancer

# DNS A record for the service
resource "google_dns_record_set" "service" {
  count = length(var.hostnames)

  name         = "${var.hostnames[count.index]}."
  type         = "A"
  ttl          = 300
  managed_zone = var.dns_zone_name
  project      = var.platform_project

  rrdatas = [data.terraform_remote_state.load_balancer.outputs.load_balancer_ip]
}

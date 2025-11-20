provider "google" {
  project = var.project_id
}

locals {
  standard_labels = {
    managed_by  = "terraform"
    environment = "prod"
    cost_center = "internal"
    component   = "dns"
  }
}

# Main DNS zone for solvigo.ai
resource "google_dns_managed_zone" "main" {
  name        = "solvigo-main-zone"
  dns_name    = var.dns_name
  description = "Main DNS zone for Solvigo platform"
  project     = var.project_id

  dnssec_config {
    state = "on"
  }

  labels = local.standard_labels
}

# Client DNS zones (e.g., acme-corp.solvigo.ai)
resource "google_dns_managed_zone" "client_zones" {
  for_each = var.client_zones

  name        = "${each.key}-solvigo-zone"
  dns_name    = "${each.key}.${var.dns_name}"
  description = each.value.description
  project     = var.project_id

  dnssec_config {
    state = "on"
  }

  labels = merge(
    local.standard_labels,
    {
      client = each.key
    }
  )
}

# NS records in main zone pointing to client zones
resource "google_dns_record_set" "client_ns_records" {
  for_each = var.client_zones

  name         = "${each.key}.${var.dns_name}"
  type         = "NS"
  ttl          = 21600 # 6 hours
  managed_zone = google_dns_managed_zone.main.name
  project      = var.project_id

  rrdatas = google_dns_managed_zone.client_zones[each.key].name_servers
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  standard_labels = {
    managed_by  = "terraform"
    environment = "prod"
    cost_center = "internal"
    component   = "networking"
  }
}

# Create VPC Network (Host Project)
resource "google_compute_network" "shared_vpc" {
  name                    = "solvigo-shared-vpc"
  auto_create_subnetworks = false
  routing_mode            = "GLOBAL"
  project                 = var.project_id
}

# Enable VPC Host Project (optional - requires compute.xpnAdmin role)
resource "google_compute_shared_vpc_host_project" "host" {
  count = var.enable_shared_vpc_host ? 1 : 0

  project = var.project_id

  depends_on = [google_compute_network.shared_vpc]
}

# Create Subnets per Region
resource "google_compute_subnetwork" "subnets" {
  for_each = { for idx, subnet in var.subnets : subnet.name => subnet }

  name          = each.value.name
  ip_cidr_range = each.value.cidr
  region        = each.value.region
  network       = google_compute_network.shared_vpc.id
  project       = var.project_id

  private_ip_google_access = true

  dynamic "log_config" {
    for_each = var.enable_flow_logs ? [1] : []
    content {
      aggregation_interval = "INTERVAL_5_SEC"
      flow_sampling        = 0.5
      metadata             = "INCLUDE_ALL_METADATA"
    }
  }
}

# Cloud Router for NAT (per region)
resource "google_compute_router" "router" {
  for_each = toset([for s in var.subnets : s.region])

  name    = "solvigo-router-${each.key}"
  region  = each.key
  network = google_compute_network.shared_vpc.id
  project = var.project_id
}

# Cloud NAT (per region)
resource "google_compute_router_nat" "nat" {
  for_each = toset([for s in var.subnets : s.region])

  name   = "solvigo-nat-${each.key}"
  router = google_compute_router.router[each.key].name
  region = each.key

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = var.nat_log_filter
  }

  project = var.project_id
}

# Firewall Rules
# Allow internal communication within VPC
resource "google_compute_firewall" "allow_internal" {
  name    = "solvigo-allow-internal"
  network = google_compute_network.shared_vpc.id
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [for subnet in var.subnets : subnet.cidr]
  priority      = 1000
}

# Allow SSH from IAP (Identity-Aware Proxy)
resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "solvigo-allow-iap-ssh"
  network = google_compute_network.shared_vpc.id
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # IAP IP range
  source_ranges = ["35.235.240.0/20"]
  priority      = 1000
}

# Allow health checks from Google Cloud Load Balancers
resource "google_compute_firewall" "allow_health_checks" {
  name    = "solvigo-allow-health-checks"
  network = google_compute_network.shared_vpc.id
  project = var.project_id

  allow {
    protocol = "tcp"
  }

  # Google Cloud health check IP ranges
  source_ranges = ["35.191.0.0/16", "130.211.0.0/22"]
  priority      = 1000
}

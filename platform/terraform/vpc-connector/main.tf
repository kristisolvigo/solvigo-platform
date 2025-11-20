terraform {
  backend "gcs" {
    bucket = "solvigo-platform-terraform-state"
    prefix = "vpc-connector"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Get the VPC network
data "google_compute_network" "shared_vpc" {
  name    = var.vpc_network
  project = var.project_id
}

# Create dedicated subnet for VPC connector
resource "google_compute_subnetwork" "vpc_connector_subnet" {
  name          = var.connector_subnet_name
  ip_cidr_range = "10.8.0.0/28"  # 16 IPs (minimum for VPC connector)
  region        = var.region
  network       = data.google_compute_network.shared_vpc.id
  project       = var.project_id

  description = "Subnet for VPC Access Connector (Cloud Run → private resources)"
}

# Create VPC Access Connector for Cloud Run to access private resources
resource "google_vpc_access_connector" "solvigo_connector" {
  name    = "solvigo-vpc-connector"
  region  = var.region
  project = var.project_id

  # Use the dedicated subnet
  subnet {
    name       = google_compute_subnetwork.vpc_connector_subnet.name
    project_id = var.project_id
  }

  # Machine type (e2-micro for cost efficiency)
  machine_type = "e2-micro"

  # Number of instances (2-10)
  min_instances = 2
  max_instances = 3
}

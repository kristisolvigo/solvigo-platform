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
}

# Get the VPC network
data "google_compute_network" "shared_vpc" {
  name    = var.vpc_network
  project = var.project_id
}

# VPC Connector for europe-north1
resource "google_compute_subnetwork" "vpc_connector_subnet_north1" {
  name          = "vpc-connector-subnet-north1"
  ip_cidr_range = "10.8.0.0/28"
  region        = "europe-north1"
  network       = data.google_compute_network.shared_vpc.id
  project       = var.project_id

  description = "Subnet for VPC Access Connector in europe-north1"
}

resource "google_vpc_access_connector" "solvigo_connector_north1" {
  name    = "solvigo-vpc-connector"
  region  = "europe-north1"
  project = var.project_id

  subnet {
    name       = google_compute_subnetwork.vpc_connector_subnet_north1.name
    project_id = var.project_id
  }

  machine_type  = "e2-micro"
  min_instances = 2
  max_instances = 3
}

# VPC Connector for europe-north2
resource "google_compute_subnetwork" "vpc_connector_subnet_north2" {
  name          = "vpc-connector-subnet-north2"
  ip_cidr_range = "10.8.1.0/28"
  region        = "europe-north2"
  network       = data.google_compute_network.shared_vpc.id
  project       = var.project_id

  description = "Subnet for VPC Access Connector in europe-north2"
}

resource "google_vpc_access_connector" "solvigo_connector_north2" {
  name    = "solvigo-connector-n2"
  region  = "europe-north2"
  project = var.project_id

  subnet {
    name       = google_compute_subnetwork.vpc_connector_subnet_north2.name
    project_id = var.project_id
  }

  machine_type  = "e2-micro"
  min_instances = 2
  max_instances = 3
}

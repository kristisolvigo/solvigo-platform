terraform {
  backend "gcs" {
    bucket = "solvigo-platform-terraform-state"
    prefix = "load-balancer"
  }

  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

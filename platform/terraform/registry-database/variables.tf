variable "project_id" {
  description = "GCP Project ID for platform"
  type        = string
  default     = "solvigo-platform-prod"
}

variable "region" {
  description = "GCP region for Cloud SQL instance"
  type        = string
  default     = "europe-north1"
}

variable "instance_name" {
  description = "Cloud SQL instance name"
  type        = string
  default     = "solvigo-registry"
}

variable "vpc_network_id" {
  description = "VPC network ID for private IP (full path)"
  type        = string
  default     = "projects/solvigo-platform-prod/global/networks/solvigo-shared-vpc"
}

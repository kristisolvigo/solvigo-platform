variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "solvigo-platform-prod"
}

variable "region" {
  description = "Region for VPC connector"
  type        = string
  default     = "europe-north1"
}

variable "connector_subnet_name" {
  description = "Subnet name for VPC connector"
  type        = string
  default     = "vpc-connector-subnet"
}

variable "vpc_network" {
  description = "VPC network name"
  type        = string
  default     = "solvigo-shared-vpc"
}

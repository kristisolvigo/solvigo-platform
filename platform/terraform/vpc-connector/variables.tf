variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "solvigo-platform-prod"
}

variable "vpc_network" {
  description = "VPC network name"
  type        = string
  default     = "solvigo-shared-vpc"
}

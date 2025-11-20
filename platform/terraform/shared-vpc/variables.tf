variable "project_id" {
  description = "GCP Project ID for platform"
  type        = string
  default     = "solvigo-platform-prod"
}

variable "region" {
  description = "Default GCP region"
  type        = string
  default     = "europe-north2"
}

variable "subnets" {
  description = "Subnets to create in Shared VPC"
  type = list(object({
    name   = string
    cidr   = string
    region = string
  }))

  default = [
    {
      name   = "solvigo-subnet-europe-north2"
      cidr   = "10.0.0.0/20"
      region = "europe-north2"
    },
    {
      name   = "solvigo-subnet-europe-north1"
      cidr   = "10.0.16.0/20"
      region = "europe-north1"
    }
  ]
}

variable "enable_flow_logs" {
  description = "Enable VPC flow logs for subnets"
  type        = bool
  default     = true
}

variable "nat_log_filter" {
  description = "Cloud NAT log filter (ALL, ERRORS_ONLY, TRANSLATIONS_ONLY)"
  type        = string
  default     = "ERRORS_ONLY"
}

variable "enable_shared_vpc_host" {
  description = "Enable Shared VPC Host (requires compute.xpnAdmin role)"
  type        = bool
  default     = true
}

variable "platform_project" {
  description = "Platform project ID where load balancer lives"
  type        = string
  default     = "solvigo-platform-prod"
}

variable "platform_state_bucket" {
  description = "Platform Terraform state bucket"
  type        = string
  default     = "solvigo-platform-terraform-state"
}

variable "client_name" {
  description = "Client name"
  type        = string
}

variable "service_name" {
  description = "Service name"
  type        = string
}

variable "cloud_run_service_name" {
  description = "Cloud Run service name"
  type        = string
}

variable "region" {
  description = "Region where Cloud Run is deployed"
  type        = string
  default     = "europe-north2"
}

variable "hostnames" {
  description = "List of hostnames for this service (without trailing dot)"
  type        = list(string)

  validation {
    condition     = length(var.hostnames) > 0
    error_message = "At least one hostname is required"
  }
}

variable "dns_zone_name" {
  description = "Cloud DNS zone name (e.g., acme-corp-solvigo-zone)"
  type        = string
}

variable "enable_cdn" {
  description = "Enable Cloud CDN"
  type        = bool
  default     = false
}

variable "enable_iap" {
  description = "Enable Identity-Aware Proxy"
  type        = bool
  default     = false
}

variable "iap_client_id" {
  description = "IAP OAuth2 client ID (required if enable_iap = true)"
  type        = string
  default     = ""
}

variable "iap_client_secret" {
  description = "IAP OAuth2 client secret (required if enable_iap = true)"
  type        = string
  default     = ""
  sensitive   = true
}

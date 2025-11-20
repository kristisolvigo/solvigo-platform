variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.service_name))
    error_message = "Service name must be lowercase alphanumeric with hyphens"
  }
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-north2"
}

variable "image" {
  description = "Container image URL"
  type        = string
  default     = "gcr.io/cloudrun/hello"  # Default hello world image
}

variable "env_vars" {
  description = "Environment variables (non-secret)"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets as environment variables (map of env var name to secret name)"
  type        = map(string)
  default     = {}
}

variable "cpu" {
  description = "CPU allocation (1000m = 1 CPU)"
  type        = string
  default     = "1000m"
}

variable "memory" {
  description = "Memory allocation"
  type        = string
  default     = "512Mi"
}

variable "port" {
  description = "Container port"
  type        = number
  default     = 8080
}

variable "min_instances" {
  description = "Minimum number of instances (0 = scale to zero)"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

variable "concurrency" {
  description = "Maximum concurrent requests per instance"
  type        = number
  default     = 80
}

variable "timeout" {
  description = "Request timeout in seconds"
  type        = number
  default     = 300
}

variable "cpu_throttling" {
  description = "Enable CPU throttling (always allocated if false)"
  type        = bool
  default     = true
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated access"
  type        = bool
  default     = true
}

variable "service_account_email" {
  description = "Service account email (creates new if empty)"
  type        = string
  default     = ""
}

variable "vpc_connector_name" {
  description = "VPC Access connector name (empty to skip VPC)"
  type        = string
  default     = ""
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}

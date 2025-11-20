variable "client_name" {
  description = "Client name (lowercase, hyphens only)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.client_name))
    error_message = "Client name must be lowercase alphanumeric with hyphens only"
  }
}

variable "project_name" {
  description = "Project name (lowercase, hyphens only)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must be lowercase alphanumeric with hyphens only"
  }
}

variable "environment" {
  description = "Environment (dev, staging, prod, or empty for single-project mode)"
  type        = string
  default     = ""

  validation {
    condition     = var.environment == "" || contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be empty, 'dev', 'staging', or 'prod'"
  }
}

variable "folder_id" {
  description = "GCP Folder ID where project will be created (format: folders/123456789)"
  type        = string

  validation {
    condition     = can(regex("^folders/[0-9]+$", var.folder_id))
    error_message = "Folder ID must be in format: folders/123456789"
  }
}

variable "billing_account_id" {
  description = "GCP Billing Account ID (format: XXXXXX-XXXXXX-XXXXXX)"
  type        = string

  validation {
    condition     = can(regex("^[A-Z0-9]{6}-[A-Z0-9]{6}-[A-Z0-9]{6}$", var.billing_account_id))
    error_message = "Billing Account ID must be in format: XXXXXX-XXXXXX-XXXXXX"
  }
}

variable "enabled_apis" {
  description = "List of GCP APIs to enable"
  type        = list(string)
  default = [
    "compute.googleapis.com",
    "run.googleapis.com",
    "vpcaccess.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
  ]
}

variable "attach_to_shared_vpc" {
  description = "Whether to attach project to Shared VPC"
  type        = bool
  default     = true
}

variable "shared_vpc_host_project" {
  description = "Shared VPC host project ID"
  type        = string
  default     = "solvigo-platform-prod"
}

variable "additional_labels" {
  description = "Additional labels to apply to the project"
  type        = map(string)
  default     = {}
}

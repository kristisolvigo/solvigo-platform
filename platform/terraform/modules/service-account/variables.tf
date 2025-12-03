variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "account_id" {
  description = "Service account ID (e.g., 'admin-api')"
  type        = string
}

variable "display_name" {
  description = "Display name for the service account"
  type        = string
}

variable "description" {
  description = "Description of the service account"
  type        = string
  default     = ""
}

variable "project_roles" {
  description = "List of IAM roles to grant at project level"
  type        = list(string)
  default     = []
}

variable "organization_id" {
  description = "Organization ID for org-level permissions (optional)"
  type        = string
  default     = null
}

variable "organization_roles" {
  description = "List of IAM roles to grant at organization level"
  type        = list(string)
  default     = []
}

variable "folder_id" {
  description = "Folder ID for folder-level permissions (optional)"
  type        = string
  default     = null
}

variable "folder_roles" {
  description = "List of IAM roles to grant at folder level"
  type        = list(string)
  default     = []
}

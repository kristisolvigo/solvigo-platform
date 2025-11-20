variable "account_id" {
  description = "Service account ID (e.g., 'acme-corp-deployer'). Max 30 chars, lowercase, hyphens only."
  type        = string

  validation {
    condition     = can(regex("^[a-z](?:[-a-z0-9]{4,28}[a-z0-9])$", var.account_id))
    error_message = "Account ID must be 6-30 characters, start with letter, contain only lowercase letters, numbers, and hyphens."
  }
}

variable "display_name" {
  description = "Human-readable name for the service account"
  type        = string
}

variable "description" {
  description = "Description of what this service account is used for"
  type        = string
  default     = ""
}

variable "project_id" {
  description = "GCP project ID where the service account will be created"
  type        = string
}

variable "project_roles" {
  description = "List of IAM roles to grant at the project level (in the same project as the SA)"
  type        = list(string)
  default     = []

  # Common roles:
  # - roles/run.admin              (Deploy Cloud Run services)
  # - roles/iam.serviceAccountUser (Act as other service accounts)
  # - roles/storage.admin          (Manage Cloud Storage)
  # - roles/cloudsql.client        (Connect to Cloud SQL)
  # - roles/secretmanager.secretAccessor (Access secrets)
  # - roles/artifactregistry.writer (Push to Artifact Registry)
}

variable "cross_project_bindings" {
  description = "Map of IAM bindings for other projects (e.g., deployer SA accessing client projects)"
  type = map(object({
    project_id = string
    role       = string
  }))
  default = {}

  # Example:
  # cross_project_bindings = {
  #   "deploy-to-acme-prod" = {
  #     project_id = "acme-corp-app1-prod"
  #     role       = "roles/run.admin"
  #   }
  # }
}

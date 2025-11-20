variable "client_name" {
  description = "Client name (e.g., 'ACME Corp')"
  type        = string
}

variable "project_name" {
  description = "Project name (e.g., 'Customer Portal')"
  type        = string
}

variable "platform_project_id" {
  description = "Platform project ID where Cloud Build and Artifact Registry live"
  type        = string
}

variable "client_project_id" {
  description = "Primary client project ID (can be overridden per environment)"
  type        = string
}

variable "client_project_ids" {
  description = "Map of environment-specific project IDs (overrides client_project_id)"
  type        = map(string)
  default     = {}
  # Example:
  # {
  #   "dev"     = "acme-app1-dev"
  #   "staging" = "acme-app1-staging"
  #   "prod"    = "acme-app1-prod"
  # }
}

variable "region" {
  description = "GCP region for Cloud Build resources"
  type        = string
  default     = "europe-north1"
}

variable "github_connection_id" {
  description = "ID of the org-wide GitHub connection (from platform)"
  type        = string
  # Format: projects/{project}/locations/{location}/connections/{name}
  # Get from: terraform output -raw github_connection_id
  #   in platform/terraform/cloud-build/
}

variable "github_repo_url" {
  description = "GitHub repository URL (HTTPS)"
  type        = string
  # Example: https://github.com/solvigo/acme-corp-app1.git
}

variable "environments" {
  description = "List of environments to create triggers for"
  type        = list(string)
  default     = ["staging", "prod"]
  # Note: Dev environment removed - use local docker-compose for development
}

variable "staging_branch_pattern" {
  description = "Branch pattern for staging deployments (regex)"
  type        = string
  default     = "^main$"  # Main branch deploys to staging
}

variable "prod_tag_pattern" {
  description = "Tag pattern for production deployments (regex)"
  type        = string
  default     = "^v[0-9]+\\.[0-9]+\\.[0-9]+$"  # v1.2.3
}

variable "require_approval_staging" {
  description = "Whether to require manual approval for staging deployments"
  type        = bool
  default     = false  # Auto-deploy to staging for faster iteration
}

variable "cloudbuild_file" {
  description = "Path to cloudbuild.yaml in the repository"
  type        = string
  default     = "cloudbuild.yaml"
}

variable "extra_substitutions" {
  description = "Additional substitution variables for Cloud Build"
  type        = map(string)
  default     = {}
  # Example:
  # {
  #   "_DOMAIN" = "acme-corp.solvigo.ai"
  #   "_DB_INSTANCE" = "acme-db"
  # }
}

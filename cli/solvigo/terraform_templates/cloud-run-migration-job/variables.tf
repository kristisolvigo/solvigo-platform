variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "job_name" {
  type        = string
  description = "Cloud Run Job name"
}

variable "region" {
  type        = string
  description = "GCP region"
  default     = "europe-north1"
}

variable "image" {
  type        = string
  description = "Container image for migration job"
  default     = "gcr.io/cloudrun/hello"  # Placeholder
}

variable "service_account_email" {
  type        = string
  description = "Service account email for job"
}

variable "deployer_sa_email" {
  type        = string
  description = "Deployer service account email (for job execution permission)"
}

variable "database_url" {
  type        = string
  description = "Database connection URL"
  default     = ""
}

variable "cloud_sql_connection_name" {
  type        = string
  description = "Cloud SQL connection name"
}

variable "vpc_connector_name" {
  type        = string
  description = "VPC connector ID for Cloud SQL access"
}

variable "env_vars" {
  type        = map(string)
  description = "Environment variables"
  default     = {}
}

variable "secrets" {
  type        = map(string)
  description = "Secrets to mount as environment variables"
  default     = {}
}

variable "cpu" {
  type        = string
  description = "CPU allocation"
  default     = "1"
}

variable "memory" {
  type        = string
  description = "Memory allocation"
  default     = "512Mi"
}

variable "timeout" {
  type        = string
  description = "Job timeout"
  default     = "600s"
}

variable "max_retries" {
  type        = number
  description = "Maximum retry attempts"
  default     = 3
}

variable "labels" {
  type        = map(string)
  description = "Labels"
  default     = {}
}

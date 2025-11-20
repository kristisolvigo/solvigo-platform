variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "database_name" {
  description = "Firestore database name (use '(default)' for default database)"
  type        = string
  default     = "(default)"
}

variable "location" {
  description = "Firestore location"
  type        = string
  default     = "eur3"
}

variable "database_type" {
  description = "Database type: FIRESTORE_NATIVE or DATASTORE_MODE"
  type        = string
  default     = "FIRESTORE_NATIVE"
}

variable "concurrency_mode" {
  description = "Concurrency mode: OPTIMISTIC or PESSIMISTIC"
  type        = string
  default     = "OPTIMISTIC"
}

variable "app_engine_integration_mode" {
  description = "App Engine integration: ENABLED or DISABLED"
  type        = string
  default     = "DISABLED"
}

variable "enable_pitr" {
  description = "Enable Point-In-Time Recovery (7-day retention)"
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

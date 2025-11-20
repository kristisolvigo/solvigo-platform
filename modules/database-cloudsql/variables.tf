variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "instance_name" {
  description = "Cloud SQL instance name"
  type        = string
}

variable "database_version" {
  description = "Database version (POSTGRES_15, POSTGRES_14, MYSQL_8_0, etc.)"
  type        = string
  default     = "POSTGRES_15"
}

variable "tier" {
  description = "Machine tier (db-f1-micro, db-g1-small, db-n1-standard-1, etc.)"
  type        = string
  default     = "db-g1-small"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-north2"
}

variable "database_name" {
  description = "Default database name"
  type        = string
  default     = "app"
}

variable "disk_size" {
  description = "Disk size in GB"
  type        = number
  default     = 10
}

variable "disk_type" {
  description = "Disk type (PD_SSD or PD_HDD)"
  type        = string
  default     = "PD_SSD"
}

variable "enable_backups" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "high_availability" {
  description = "Enable high availability (regional)"
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "public_ip" {
  description = "Assign public IP"
  type        = bool
  default     = false
}

variable "private_network" {
  description = "VPC network self-link for private IP (null for no private IP)"
  type        = string
  default     = null
}

variable "max_connections" {
  description = "Maximum number of connections"
  type        = number
  default     = 100
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default     = {}
}

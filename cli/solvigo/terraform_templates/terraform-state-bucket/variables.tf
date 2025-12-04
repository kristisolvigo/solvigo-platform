variable "project_id" {
  description = "GCP Project ID where bucket will be created"
  type        = string
}

variable "bucket_name" {
  description = "Bucket name in format {clientsubdomain}-{projectsubdomain}-tfstate"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]+-[a-z0-9-]+-tfstate$", var.bucket_name))
    error_message = "Bucket name must be in format {clientsubdomain}-{projectsubdomain}-tfstate (e.g., acme-portal-tfstate)"
  }
}

variable "location" {
  description = "Bucket location"
  type        = string
  default     = "europe-north2"
}

variable "keep_versions" {
  description = "Number of state versions to keep"
  type        = number
  default     = 30
}

variable "kms_key_name" {
  description = "KMS key for encryption (optional)"
  type        = string
  default     = null
}

variable "terraform_sa_member" {
  description = "Terraform service account member (e.g., serviceAccount:terraform@project.iam.gserviceaccount.com)"
  type        = string
}

variable "admin_members" {
  description = "List of admin members who can view state (optional)"
  type        = list(string)
  default     = null
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default     = {}
}

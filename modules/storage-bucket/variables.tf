variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "bucket_name" {
  description = "Bucket name (globally unique)"
  type        = string
}

variable "location" {
  description = "Bucket location"
  type        = string
  default     = "europe-north2"
}

variable "enable_versioning" {
  description = "Enable object versioning"
  type        = bool
  default     = false
}

variable "force_destroy" {
  description = "Allow bucket deletion even if not empty"
  type        = bool
  default     = false
}

variable "lifecycle_rules" {
  description = "Lifecycle rules for objects"
  type = list(object({
    action             = string
    age                = number
    num_newer_versions = number
    with_state         = string
  }))
  default = []
}

variable "cors_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["*"]
}

variable "cors_methods" {
  description = "CORS allowed methods"
  type        = list(string)
  default     = ["GET", "HEAD", "PUT", "POST", "DELETE"]
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default     = {}
}

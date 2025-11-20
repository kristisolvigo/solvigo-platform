variable "project_id" {
  description = "GCP Project ID for platform"
  type        = string
  default     = "solvigo-platform-prod"
}

variable "domain" {
  description = "Base domain name"
  type        = string
  default     = "solvigo.ai"
}

variable "enable_ssl" {
  description = "Enable HTTPS/SSL"
  type        = bool
  default     = true
}

variable "ssl_domains" {
  description = "List of domains for SSL certificate (wildcards supported)"
  type        = list(string)
  default = [
    "solvigo.ai",
    "*.solvigo.ai",
    "*.*.solvigo.ai"
  ]
}

variable "enable_cdn" {
  description = "Enable Cloud CDN"
  type        = bool
  default     = true
}

variable "enable_iap" {
  description = "Enable Identity-Aware Proxy"
  type        = bool
  default     = false
}

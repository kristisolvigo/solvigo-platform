variable "project_id" {
  description = "GCP Project ID for platform"
  type        = string
  default     = "solvigo-platform-prod"
}

variable "domain" {
  description = "Base domain name (e.g., solvigo.ai)"
  type        = string
  default     = "solvigo.ai"
}

variable "dns_name" {
  description = "DNS name (must end with dot, e.g., solvigo.ai.)"
  type        = string
  default     = "solvigo.ai."
}

variable "client_zones" {
  description = "Map of client subdomains to create (e.g., {acme-corp = {}, techstart = {}})"
  type = map(object({
    description = optional(string, "Client DNS zone")
  }))
  default = {
    # Example:
    # "acme-corp" = {
    #   description = "ACME Corporation DNS zone"
    # }
  }
}

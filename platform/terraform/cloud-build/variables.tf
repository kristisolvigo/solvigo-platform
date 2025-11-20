variable "project_id" {
  description = "GCP Project ID for platform"
  type        = string
  default     = "solvigo-platform-prod"
}

variable "region" {
  description = "Default region for Cloud Build resources"
  type        = string
  default     = "europe-north2"  # Matches your Cloud Build connection region
}

variable "github_connection_name" {
  description = "Name of GitHub connection (created manually in GCP console)"
  type        = string
  default     = "solvigo-github-connection"

  # To find the connection name after creating in console:
  # gcloud builds connections list \
  #   --region=europe-north2 \
  #   --project=solvigo-platform-prod
}

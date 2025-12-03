variable "project_id" {
  description = "GCP Project ID (solvigo-platform-prod)"
  type        = string
}

variable "region" {
  description = "Default region"
  type        = string
  default     = "europe-north1"
}

variable "clients_folder_id" {
  description = "GCP Folder ID where client projects are created"
  type        = string
  default     = null
}

variable "cloud_sql_instance" {
  description = "Cloud SQL instance connection name"
  type        = string
  default     = "solvigo-platform-prod:europe-north1:solvigo-registry"
}

variable "vpc_connector_id" {
  description = "VPC Access Connector ID"
  type        = string
  default     = "projects/solvigo-platform-prod/locations/europe-north1/connectors/solvigo-vpc-connector"
}

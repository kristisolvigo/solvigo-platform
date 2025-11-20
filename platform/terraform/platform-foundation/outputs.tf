output "enabled_services" {
  description = "List of enabled GCP services"
  value = [
    google_project_service.compute.service,
    google_project_service.dns.service,
    google_project_service.servicenetworking.service,
    google_project_service.cloudbuild.service,
    google_project_service.artifactregistry.service,
    google_project_service.secretmanager.service,
    google_project_service.run.service,
    google_project_service.vpcaccess.service,
    google_project_service.logging.service,
    google_project_service.monitoring.service,
  ]
}

output "project_id" {
  description = "Platform project ID"
  value       = var.project_id
}

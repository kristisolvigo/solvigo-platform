output "deployer_sa_email" {
  description = "Deployer service account email"
  value       = module.deployer_sa.email
}

output "deployer_sa_name" {
  description = "Deployer service account full name"
  value       = module.deployer_sa.name
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository name"
  value       = google_artifact_registry_repository.images.name
}

output "artifact_registry_url" {
  description = "Full URL for pushing Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.platform_project_id}/${google_artifact_registry_repository.images.name}"
}

output "github_repository_id" {
  description = "Cloud Build v2 repository ID"
  value       = google_cloudbuildv2_repository.repo.id
}

output "trigger_ids" {
  description = "Map of trigger IDs by environment"
  value = {
    dev     = try(google_cloudbuild_trigger.dev[0].id, null)
    staging = try(google_cloudbuild_trigger.staging[0].id, null)
    prod    = try(google_cloudbuild_trigger.prod[0].id, null)
  }
}

output "trigger_names" {
  description = "Map of trigger names by environment"
  value = {
    dev     = try(google_cloudbuild_trigger.dev[0].name, null)
    staging = try(google_cloudbuild_trigger.staging[0].name, null)
    prod    = try(google_cloudbuild_trigger.prod[0].name, null)
  }
}

output "summary" {
  description = "Summary of created resources"
  value = {
    deployer_sa        = module.deployer_sa.email
    artifact_repo      = google_artifact_registry_repository.images.name
    github_repo        = google_cloudbuildv2_repository.repo.name
    triggers_created   = length(google_cloudbuild_trigger.dev) + length(google_cloudbuild_trigger.staging) + length(google_cloudbuild_trigger.prod)
    environments       = var.environments
  }
}

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

locals {
  # Normalize names for resource naming
  client_slug  = lower(replace(var.client_name, " ", "-"))
  project_slug = lower(replace(var.project_name, " ", "-"))

  # Full resource prefix
  resource_prefix = "${local.client_slug}-${local.project_slug}"
}

# 1. Create deployer service account (in platform project)
module "deployer_sa" {
  source = "../../../modules/service-account"

  account_id   = "${local.resource_prefix}-deployer"
  display_name = "${var.client_name} ${var.project_name} Deployer"
  description  = "Cloud Build service account for deploying ${var.client_name}/${var.project_name}"
  project_id   = var.platform_project_id

  # Platform project roles
  project_roles = [
    "roles/iam.serviceAccountUser",    # Can act as other service accounts
    "roles/artifactregistry.writer",   # Push to Artifact Registry
    "roles/logging.logWriter",         # Write build logs
  ]

  # Grant access to client project(s)
  cross_project_bindings = {
    for env in var.environments : "deploy-${env}" => {
      project_id = lookup(var.client_project_ids, env, var.client_project_id)
      role       = "roles/run.admin"
    }
  }
}

# Additional permissions needed in client projects
resource "google_project_iam_member" "deployer_client_permissions" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",  # Access secrets during deployment
    "roles/cloudsql.client",               # Configure Cloud SQL connections
    "roles/compute.networkUser",           # Use VPC connectors
  ])

  project = var.client_project_id
  role    = each.value
  member  = module.deployer_sa.member
}

# 2. Create Artifact Registry repository (per client/project)
resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = local.resource_prefix
  description   = "Docker images for ${var.client_name}/${var.project_name}"
  format        = "DOCKER"
  project       = var.platform_project_id

  labels = {
    client      = local.client_slug
    project     = local.project_slug
    managed_by  = "terraform"
    cost_center = "client-billable"
  }
}

# Grant deployer SA write access (already has it via project role, but explicit is good)
resource "google_artifact_registry_repository_iam_member" "deployer_writer" {
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.name
  project    = var.platform_project_id
  role       = "roles/artifactregistry.writer"
  member     = module.deployer_sa.member
}

# 3. Link GitHub repository (reuses org-wide connection)
resource "google_cloudbuildv2_repository" "repo" {
  location          = var.region
  name              = local.resource_prefix
  parent_connection = var.github_connection_id
  remote_uri        = var.github_repo_url
  project           = var.platform_project_id

  annotations = {
    client  = var.client_name
    project = var.project_name
  }
}

# 4. Create Cloud Build triggers
# Note: Dev environment removed - developers use local docker-compose
# Staging auto-deploys on push to main for fast iteration
# Production requires tag + manual approval

# STAGING: Auto-deploy on push to main
resource "google_cloudbuild_trigger" "staging" {
  count = contains(var.environments, "staging") ? 1 : 0

  name        = "${local.resource_prefix}-staging"
  location    = var.region
  description = "Deploy ${var.client_name}/${var.project_name} to staging"
  project     = var.platform_project_id

  repository_event_config {
    repository = google_cloudbuildv2_repository.repo.id
    push {
      branch = var.staging_branch_pattern
    }
  }

  filename        = var.cloudbuild_file
  service_account = module.deployer_sa.id

  # Optional manual approval for staging (default: false for faster iteration)
  dynamic "approval_config" {
    for_each = var.require_approval_staging ? [1] : []
    content {
      approval_required = true
    }
  }

  substitutions = merge(
    {
      _CLIENT_NAME     = var.client_name
      _PROJECT_NAME    = var.project_name
      _ENVIRONMENT     = "staging"
      _REGION          = var.region
      _SERVICE_ACCOUNT = module.deployer_sa.email
      _ARTIFACT_REPO   = "${var.region}-docker.pkg.dev/${var.platform_project_id}/${google_artifact_registry_repository.images.name}"
      _GCP_PROJECT     = lookup(var.client_project_ids, "staging", var.client_project_id)
    },
    var.extra_substitutions
  )

  tags = ["staging", "auto-deploy", local.client_slug, local.project_slug]
}

# PROD: Tag-based deployment with approval
resource "google_cloudbuild_trigger" "prod" {
  count = contains(var.environments, "prod") ? 1 : 0

  name        = "${local.resource_prefix}-prod"
  location    = var.region
  description = "Deploy ${var.client_name}/${var.project_name} to prod (tag-based)"
  project     = var.platform_project_id

  repository_event_config {
    repository = google_cloudbuildv2_repository.repo.id
    push {
      tag = var.prod_tag_pattern
    }
  }

  filename        = var.cloudbuild_file
  service_account = module.deployer_sa.id

  # Always require approval for production
  approval_config {
    approval_required = true
  }

  substitutions = merge(
    {
      _CLIENT_NAME     = var.client_name
      _PROJECT_NAME    = var.project_name
      _ENVIRONMENT     = "prod"
      _REGION          = var.region
      _SERVICE_ACCOUNT = module.deployer_sa.email
      _ARTIFACT_REPO   = "${var.region}-docker.pkg.dev/${var.platform_project_id}/${google_artifact_registry_repository.images.name}"
      _GCP_PROJECT     = lookup(var.client_project_ids, "prod", var.client_project_id)
    },
    var.extra_substitutions
  )

  tags = ["prod", "approval-required", "tag-deploy", local.client_slug, local.project_slug]
}

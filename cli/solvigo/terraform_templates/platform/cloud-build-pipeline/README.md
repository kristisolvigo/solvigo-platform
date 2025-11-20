# Cloud Build Pipeline Module

Complete CI/CD pipeline setup for client projects using Cloud Build, GitHub, and Artifact Registry.

## What This Module Creates

1. **Deployer Service Account** - Cloud Build uses this to deploy resources
2. **Artifact Registry Repository** - Stores Docker images per client/project
3. **GitHub Repository Link** - Connects your GitHub repo to Cloud Build
4. **Build Triggers** - Automated triggers for dev, staging, prod

## Features

- ✅ Automated deployment from GitHub (push/tag-based)
- ✅ Separate environments (dev, staging, prod)
- ✅ Manual approval for staging/prod
- ✅ Artifact Registry for Docker images
- ✅ Secure service account management
- ✅ Cross-project permissions (platform → client)
- ✅ Customizable build configurations

## Architecture

```
GitHub Repo (push/tag)
    ↓
Cloud Build Trigger (in platform project)
    ↓
Build with cloudbuild.yaml
    ↓
Push to Artifact Registry (in platform project)
    ↓
Deploy to Cloud Run (in client project)
```

## Prerequisites

### 1. Platform GitHub Connection

The org-wide GitHub connection must be created first:

```bash
cd platform/terraform/cloud-build
terraform apply
# Note the github_connection_id output
```

### 2. GitHub Repository

- Repository must exist in your GitHub org
- Cloud Build GitHub App must have access to it
- Repository should contain a `cloudbuild.yaml` file

## Usage

### Basic Setup (Single Project)

```hcl
# In clients/{client}/{project}/terraform/cicd.tf

# Get GitHub connection from platform state
data "terraform_remote_state" "platform_cloudbuild" {
  backend = "gcs"
  config = {
    bucket = "solvigo-platform-terraform-state"
    prefix = "cloud-build"
  }
}

module "cicd" {
  source = "../../../../platform/modules/cloud-build-pipeline"

  client_name         = "ACME Corp"
  project_name        = "Customer Portal"
  platform_project_id = "solvigo-platform-prod"
  client_project_id   = "acme-corp-customer-portal-prod"

  github_connection_id = data.terraform_remote_state.platform_cloudbuild.outputs.github_connection_id
  github_repo_url      = "https://github.com/solvigo/acme-corp-customer-portal.git"

  region = "europe-north1"
}

output "deployer_sa" {
  value = module.cicd.deployer_sa_email
}

output "artifact_repo" {
  value = module.cicd.artifact_registry_url
}
```

### Multi-Environment Setup (Separate Projects)

```hcl
module "cicd" {
  source = "../../../../platform/modules/cloud-build-pipeline"

  client_name         = "ACME Corp"
  project_name        = "Customer Portal"
  platform_project_id = "solvigo-platform-prod"
  client_project_id   = "acme-corp-customer-portal-prod"  # Default/fallback

  # Override per environment
  client_project_ids = {
    dev     = "acme-corp-customer-portal-dev"
    staging = "acme-corp-customer-portal-staging"
    prod    = "acme-corp-customer-portal-prod"
  }

  github_connection_id = data.terraform_remote_state.platform_cloudbuild.outputs.github_connection_id
  github_repo_url      = "https://github.com/solvigo/acme-corp-customer-portal.git"

  # Custom branch/tag patterns
  dev_branch_pattern     = "^(main|develop)$"
  staging_branch_pattern = "^release/.*$"
  prod_tag_pattern       = "^v[0-9]+\\.[0-9]+\\.[0-9]+$"  # v1.2.3

  # Custom substitutions
  extra_substitutions = {
    _DOMAIN      = "acme-corp.solvigo.ai"
    _DB_INSTANCE = "acme-db-prod"
  }
}
```

### Same-Project Separation (Different Services)

```hcl
module "cicd" {
  source = "../../../../platform/modules/cloud-build-pipeline"

  client_name         = "ACME Corp"
  project_name        = "Customer Portal"
  platform_project_id = "solvigo-platform-prod"
  client_project_id   = "acme-corp-customer-portal"  # Same project for all envs

  github_connection_id = data.terraform_remote_state.platform_cloudbuild.outputs.github_connection_id
  github_repo_url      = "https://github.com/solvigo/acme-corp-customer-portal.git"

  # In this case, Cloud Run services are named:
  # - customer-portal-dev
  # - customer-portal-staging
  # - customer-portal-prod
}
```

## Deployment Workflow

### Development
```bash
git push origin main
# → Automatically triggers Cloud Build
# → Builds Docker image
# → Pushes to Artifact Registry
# → Deploys to dev environment
# → NO approval needed
```

### Staging
```bash
git checkout -b staging
git push origin staging
# → Triggers Cloud Build
# → Requires manual approval in GCP Console
# → Deploys to staging environment
```

### Production
```bash
git tag v1.0.0
git push origin v1.0.0
# → Triggers Cloud Build
# → Requires manual approval
# → Deploys to production environment
```

## Created Resources

### In Platform Project (`solvigo-platform-prod`)

```
Service Accounts:
  └── {client}-{project}-deployer@solvigo-platform-prod.iam.gserviceaccount.com

Artifact Registry:
  └── europe-north1-docker.pkg.dev/solvigo-platform-prod/{client}-{project}/
        ├── {service}:latest
        ├── {service}:dev
        ├── {service}:staging
        ├── {service}:prod
        └── {service}:{git-sha}

Cloud Build:
  ├── Repository: {client}-{project}
  └── Triggers:
        ├── {client}-{project}-dev
        ├── {client}-{project}-staging
        └── {client}-{project}-prod
```

### In Client Project(s)

```
IAM Permissions (for deployer SA):
  ├── roles/run.admin
  ├── roles/secretmanager.secretAccessor
  ├── roles/cloudsql.client
  └── roles/compute.networkUser
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| client_name | Client name | string | - | yes |
| project_name | Project name | string | - | yes |
| platform_project_id | Platform project ID | string | - | yes |
| client_project_id | Client project ID (default) | string | - | yes |
| client_project_ids | Per-environment project IDs | map(string) | {} | no |
| github_connection_id | GitHub connection ID | string | - | yes |
| github_repo_url | GitHub repo URL (HTTPS) | string | - | yes |
| region | GCP region | string | europe-north1 | no |
| environments | Environments to create | list(string) | [dev, staging, prod] | no |
| dev_branch_pattern | Dev branch regex | string | ^main$ | no |
| staging_branch_pattern | Staging branch regex | string | ^staging$ | no |
| prod_tag_pattern | Prod tag regex | string | ^v[0-9]+\.[0-9]+\.[0-9]+$ | no |
| require_approval_staging | Require approval for staging | bool | true | no |
| cloudbuild_file | Path to cloudbuild.yaml | string | cloudbuild.yaml | no |
| extra_substitutions | Extra Cloud Build substitutions | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| deployer_sa_email | Deployer service account email |
| artifact_registry_url | Artifact Registry URL for pushing images |
| github_repository_id | Cloud Build repository ID |
| trigger_ids | Map of trigger IDs by environment |
| summary | Summary of all created resources |

## cloudbuild.yaml Template

Copy the template from `templates/cloudbuild.yaml` to your repository:

```bash
cp platform/modules/cloud-build-pipeline/templates/cloudbuild.yaml \
   clients/{client}/{project}/app/cloudbuild.yaml
```

Edit the template to customize:
- Service name
- Dockerfile path
- Cloud Run flags (VPC, secrets, env vars)
- Add smoke tests

## Manual Trigger

Trigger a build manually:

```bash
gcloud builds triggers run acme-corp-customer-portal-dev \
  --project=solvigo-platform-prod \
  --region=europe-north1 \
  --branch=main
```

## View Build Logs

```bash
# List recent builds
gcloud builds list \
  --project=solvigo-platform-prod \
  --region=europe-north1 \
  --limit=10

# Stream build logs
gcloud builds log <BUILD_ID> \
  --project=solvigo-platform-prod \
  --region=europe-north1 \
  --stream
```

## Security Best Practices

1. **Separate Service Accounts**: Deployer SA ≠ Runtime SA
2. **Least Privilege**: Only grant necessary roles
3. **Approval Required**: Always for production
4. **Tag-based Prod**: Use semantic versioning (v1.2.3)
5. **Secret Management**: Use Secret Manager, not env vars in build

## Customization Examples

### Add Smoke Tests

Edit `cloudbuild.yaml`:
```yaml
steps:
  # ... build and deploy steps ...

  - name: 'gcr.io/cloud-builders/curl'
    id: 'smoke-test'
    args:
      - '-f'
      - 'https://$_SERVICE_NAME.$_DOMAIN/health'
    waitFor: ['deploy-cloudrun']
```

### Multi-Region Deployment

```yaml
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'deploy-europe'
    args: ['run', 'deploy', ..., '--region=europe-north1']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'deploy-us'
    args: ['run', 'deploy', ..., '--region=us-central1']
    waitFor: ['deploy-europe']
```

### Terraform Deployment

```yaml
  - name: 'hashicorp/terraform:latest'
    id: 'terraform-apply'
    args:
      - 'apply'
      - '-auto-approve'
    dir: 'terraform/'
```

## Troubleshooting

### Trigger Not Firing

1. Check GitHub App has repo access
2. Verify branch/tag pattern matches
3. Check `cloudbuild.yaml` exists in repo

### Permission Denied

```bash
# Grant deployer SA the needed role
gcloud projects add-iam-policy-binding {CLIENT_PROJECT} \
  --member="serviceAccount:{DEPLOYER_SA}" \
  --role="roles/run.admin"
```

### Build Timeout

Increase timeout in `cloudbuild.yaml`:
```yaml
timeout: '1800s'  # 30 minutes
```

## Cost Optimization

- Use smaller machine types for simple builds
- Enable build caching (`--cache-from`)
- Clean up old images in Artifact Registry
- Set max builds concurrency

## Next Steps

After deploying this module:

1. Add `cloudbuild.yaml` to your repository
2. Push to trigger first build
3. Configure Cloud Run service settings
4. Set up monitoring and alerts
5. Document your deployment process

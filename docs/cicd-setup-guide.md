# CI/CD Setup Guide

Complete guide for setting up the centralized Cloud Build CI/CD pipeline for Solvigo platform.

## Overview

The Solvigo platform uses a **centralized CI/CD approach**:

- ✅ **One GitHub connection** for the entire organization
- ✅ **Central Cloud Build** in platform project
- ✅ **Central Artifact Registry** in platform project
- ✅ **Deployer service accounts** with cross-project permissions
- ✅ **Per-client repositories** and triggers
- ✅ **Automated deployments** with approval gates

## Architecture

```
GitHub Organization
  └── Repo: solvigo/acme-corp-app1
        ↓ (push/tag)
Platform Project (solvigo-platform-prod)
  ├── GitHub Connection (org-wide, reusable)
  ├── Cloud Build Triggers
  │     ├── acme-corp-app1-dev (auto)
  │     ├── acme-corp-app1-staging (approval)
  │     └── acme-corp-app1-prod (approval)
  ├── Artifact Registry
  │     └── acme-corp-app1/
  │           ├── backend:latest
  │           ├── backend:dev
  │           └── backend:abc123
  └── Service Account
        └── acme-corp-app1-deployer@...
              ↓ (has permissions)
Client Project (acme-corp-app1-prod)
  └── Cloud Run: backend
```

## One-Time Platform Setup

### Step 1: Get GitHub App Credentials

You mentioned you already have a Cloud Build GitHub App installed. Now you need:

#### A. GitHub App Installation ID

```bash
# Method 1: Via GitHub UI
# 1. Go to: https://github.com/organizations/{YOUR_ORG}/settings/installations
# 2. Click on your Cloud Build GitHub App
# 3. Copy the number from URL: .../installations/{THIS_NUMBER}

# Method 2: Via GitHub API
ORG_NAME="your-org"
GITHUB_TOKEN="your-token"  # Needs admin:org

curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/orgs/$ORG_NAME/installations" \
  | jq '.[] | select(.app_slug == "google-cloud-build") | .id'
```

#### B. GitHub Personal Access Token (PAT)

**Important**: Use a bot/service account, NOT your personal account!

1. Create bot user: `solvigo-bot` (or similar)
2. Add bot to your GitHub org
3. Generate PAT: https://github.com/settings/tokens/new
   - Name: "Solvigo Cloud Build"
   - Scopes: ✅ `repo` (Full control of private repositories)
4. Copy the token (starts with `ghp_`)

### Step 2: Deploy Platform GitHub Connection

```bash
cd platform/terraform/cloud-build

# Create terraform.tfvars
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your Installation ID
# github_app_installation_id = "12345678"

# Set GitHub token via environment (NEVER commit this!)
export TF_VAR_github_oauth_token="ghp_xxxxxxxxxxxxxxxxxxxx"

# Deploy
terraform init
terraform plan
terraform apply

# Save the connection ID
terraform output -raw github_connection_id
# Output: projects/solvigo-platform-prod/locations/europe-north1/connections/solvigo-github
```

### Step 3: Store Connection ID

Add to `.solvigo_config`:

```bash
echo "export SOLVIGO_GITHUB_CONNECTION_ID=\"$(terraform output -raw github_connection_id)\"" \
  >> ../../../.solvigo_config

source ../../../.solvigo_config
```

**Done!** The platform-level setup is complete. This only needs to be done once.

---

## Per-Client Setup

For each new client project, follow these steps:

### Option A: Using CLI (Recommended)

```bash
solvigo init  # or solvigo import

# When prompted:
# "Setup CI/CD pipeline? (Y/n)" → Y
# "GitHub repository URL:" → https://github.com/solvigo/acme-corp-app1.git

# CLI will:
# 1. Generate clients/{client}/{project}/terraform/cicd.tf
# 2. Generate cloudbuild.yaml template
# 3. Run terraform apply
```

### Option B: Manual Setup

#### 1. Create Client Terraform Configuration

`clients/acme-corp/app1/terraform/cicd.tf`:

```hcl
# Get platform GitHub connection
data "terraform_remote_state" "platform_cloudbuild" {
  backend = "gcs"
  config = {
    bucket = "solvigo-platform-terraform-state"
    prefix = "cloud-build"
  }
}

# Setup CI/CD pipeline
module "cicd" {
  source = "../../../../platform/modules/cloud-build-pipeline"

  client_name         = var.client_name
  project_name        = var.project_name
  platform_project_id = "solvigo-platform-prod"
  client_project_id   = var.client_project_id

  github_connection_id = data.terraform_remote_state.platform_cloudbuild.outputs.github_connection_id
  github_repo_url      = "https://github.com/solvigo/acme-corp-app1.git"

  region       = var.region
  environments = ["dev", "staging", "prod"]
}

output "cicd_summary" {
  description = "CI/CD setup summary"
  value       = module.cicd.summary
}

output "deployer_service_account" {
  description = "Service account used by Cloud Build"
  value       = module.cicd.deployer_sa_email
}

output "artifact_registry" {
  description = "Docker image repository URL"
  value       = module.cicd.artifact_registry_url
}
```

#### 2. Apply Terraform

```bash
cd clients/acme-corp/app1/terraform
terraform init
terraform plan
terraform apply
```

#### 3. Copy cloudbuild.yaml Template

```bash
# Copy template to your repo
cp ../../../../platform/modules/cloud-build-pipeline/templates/cloudbuild.yaml \
   ../app/cloudbuild.yaml

# Customize it
cd ../app
nano cloudbuild.yaml  # Edit SERVICE_NAME, add env vars, etc.

# Commit and push
git add cloudbuild.yaml
git commit -m "Add Cloud Build configuration"
git push origin main
```

---

## First Deployment

### Trigger Dev Build

```bash
# Push to main branch
git push origin main

# Watch the build
gcloud builds list \
  --project=solvigo-platform-prod \
  --region=europe-north1 \
  --filter="trigger_id:acme-corp-app1-dev" \
  --limit=1

# Stream logs
BUILD_ID=$(gcloud builds list --project=solvigo-platform-prod --region=europe-north1 --limit=1 --format="value(id)")
gcloud builds log $BUILD_ID --project=solvigo-platform-prod --region=europe-north1 --stream
```

### Deploy to Staging

```bash
# Create staging branch
git checkout -b staging
git push origin staging

# Approve in Cloud Build console:
# https://console.cloud.google.com/cloud-build/builds?project=solvigo-platform-prod
```

### Deploy to Production

```bash
# Tag a release
git tag v1.0.0
git push origin v1.0.0

# Approve in Cloud Build console
```

---

## Environment Strategies

### Strategy 1: Separate Projects (Recommended)

```hcl
client_project_ids = {
  dev     = "acme-corp-app1-dev"
  staging = "acme-corp-app1-staging"
  prod    = "acme-corp-app1-prod"
}
```

**Pros**:
- Strong isolation
- Clear billing separation
- Prod safety

**Cons**:
- More projects to manage
- More complex IAM

### Strategy 2: Same Project, Different Services

```hcl
client_project_id = "acme-corp-app1"

# Cloud Run services named:
# - app1-dev
# - app1-staging
# - app1-prod
```

**Pros**:
- Simpler setup
- Easier secret sharing
- Fewer projects

**Cons**:
- Less isolation
- Harder cost tracking

---

## Common Customizations

### Add Environment Variables

In `cloudbuild.yaml`:

```yaml
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'run'
      - 'deploy'
      - '--set-env-vars=ENV=$_ENVIRONMENT,DEBUG=false'
      # ...
```

### Add Secrets

```yaml
      - '--set-secrets=DB_PASSWORD=db-password:latest,API_KEY=api-key:latest'
```

### Connect to Cloud SQL

```yaml
      - '--add-cloudsql-instances=$_DB_INSTANCE'
```

### Use VPC Connector

```yaml
      - '--vpc-connector=solvigo-vpc-connector'
      - '--vpc-egress=private-ranges-only'
```

### Add Smoke Tests

```yaml
  - name: 'gcr.io/cloud-builders/curl'
    id: 'smoke-test'
    args:
      - '-f'
      - 'https://$_SERVICE_NAME-$_ENVIRONMENT.acme-corp.solvigo.ai/health'
    waitFor: ['deploy-cloudrun']
```

---

## Monitoring & Alerts

### View Build History

```bash
gcloud builds list \
  --project=solvigo-platform-prod \
  --region=europe-north1 \
  --limit=20
```

### Set Up Slack Notifications

1. Create Pub/Sub topic for build events
2. Create Cloud Function to format & send to Slack
3. Subscribe function to topic

(Future enhancement - not yet implemented)

---

## Troubleshooting

### Build Not Triggering

**Check 1**: GitHub App has access to repo
```bash
# Verify in GitHub: Settings → Installed GitHub Apps → Cloud Build
```

**Check 2**: Trigger configuration
```bash
gcloud builds triggers describe acme-corp-app1-dev \
  --project=solvigo-platform-prod \
  --region=europe-north1
```

**Check 3**: Branch/tag pattern matches
```bash
# Dev trigger watches: ^main$
# Staging trigger watches: ^staging$
# Prod trigger watches: ^v[0-9]+\.[0-9]+\.[0-9]+$
```

### Permission Denied During Deployment

```bash
# Grant deployer SA the missing role
gcloud projects add-iam-policy-binding acme-corp-app1-prod \
  --member="serviceAccount:acme-corp-app1-deployer@solvigo-platform-prod.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

### Image Not Found

```bash
# Verify image was pushed
gcloud artifacts docker images list \
  europe-north1-docker.pkg.dev/solvigo-platform-prod/acme-corp-app1 \
  --limit=10
```

### Build Timeout

Increase in `cloudbuild.yaml`:
```yaml
timeout: '1800s'  # 30 minutes
```

---

## Security Best Practices

1. ✅ **Use bot account** for GitHub PAT, not personal
2. ✅ **Store PAT in Secret Manager**, not in code
3. ✅ **Rotate PAT** every 90 days
4. ✅ **Require approval** for staging/prod
5. ✅ **Use semantic versioning** for prod tags
6. ✅ **Separate deployer SA** from runtime SA
7. ✅ **Grant least privilege** to service accounts
8. ✅ **Enable build logs** in Cloud Logging
9. ✅ **Review builds** before approving
10. ✅ **Monitor for anomalies** in build patterns

---

## Cost Optimization

1. Use `E2_HIGHCPU_8` (not `N1_HIGHCPU_32`)
2. Set timeouts to prevent runaway builds
3. Enable Docker layer caching
4. Clean up old Artifact Registry images
5. Use build triggers, not scheduled builds

```bash
# Clean up old images (keep last 10 per tag)
gcloud artifacts docker images list \
  europe-north1-docker.pkg.dev/solvigo-platform-prod/acme-corp-app1 \
  --format="value(version)" \
  | tail -n +11 \
  | xargs -I {} gcloud artifacts docker images delete \
      europe-north1-docker.pkg.dev/solvigo-platform-prod/acme-corp-app1@{}
```

---

## What's Next?

After setting up CI/CD:

1. **Configure Cloud Run**: Set CPU, memory, scaling limits
2. **Set up monitoring**: Cloud Monitoring dashboards
3. **Enable alerts**: Build failures, deployment errors
4. **Document runbooks**: How to rollback, troubleshoot
5. **Create staging checklist**: What to test before prod
6. **Automate rollbacks**: If smoke tests fail

---

## Resources

- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Artifact Registry Docs](https://cloud.google.com/artifact-registry/docs)
- [Cloud Build Triggers](https://cloud.google.com/build/docs/automating-builds/create-manage-triggers)
- [Service Accounts Best Practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)

---

## Getting Help

- Check build logs first
- Review trigger configuration
- Verify IAM permissions
- Test with manual trigger
- Check GitHub App installation

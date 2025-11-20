# Platform Foundation

This Terraform configuration enables the required GCP APIs for the Solvigo platform.

## Purpose

This is the **first** Terraform configuration to run after the bootstrap script. It enables all the APIs needed by the other platform components (Shared VPC, DNS, Load Balancer).

## Why Separate from Bootstrap Script?

The setup script (`scripts/setup-platform.sh`) only enables the **absolute minimum** APIs needed for Terraform to function:
- `storage.googleapis.com` - For Terraform state bucket
- `cloudresourcemanager.googleapis.com` - For managing GCP resources
- `iam.googleapis.com` - For service accounts
- `serviceusage.googleapis.com` - So Terraform can enable other APIs

All other APIs are managed by **this Terraform configuration**, keeping infrastructure as code.

## APIs Enabled

This configuration enables:
- `compute.googleapis.com` - Compute Engine, VPC, networking
- `dns.googleapis.com` - Cloud DNS
- `servicenetworking.googleapis.com` - VPC peering, service networking
- `cloudbuild.googleapis.com` - Cloud Build CI/CD
- `artifactregistry.googleapis.com` - Docker container registry
- `secretmanager.googleapis.com` - Secret Manager
- `run.googleapis.com` - Cloud Run
- `vpcaccess.googleapis.com` - Serverless VPC Access
- `logging.googleapis.com` - Cloud Logging
- `monitoring.googleapis.com` - Cloud Monitoring

## Usage

### Deploy

```bash
cd platform/terraform/platform-foundation
terraform init
terraform plan
terraform apply
```

### Verify

```bash
terraform output enabled_services
```

Or check directly:

```bash
gcloud services list --enabled --project=solvigo-platform-prod
```

## Deployment Order

1. **Bootstrap Script** (`./scripts/setup-platform.sh`)
   - Creates folder, project, state bucket
   - Enables minimal APIs

2. **Platform Foundation** (this) ← **YOU ARE HERE**
   - Enables all required APIs

3. **Shared VPC** (`platform/terraform/shared-vpc`)
   - Creates VPC, subnets, NAT

4. **Cloud DNS** (`platform/terraform/dns`)
   - Creates DNS zones

5. **Load Balancer** (`platform/terraform/load-balancer`)
   - Creates global LB with SSL

## Time to Complete

~2-3 minutes (API enablement)

## Cost

API enablement is **free**. You only pay for resource usage.

## Notes

- APIs are set with `disable_on_destroy = false` for safety
- If you destroy this config, APIs remain enabled
- This is intentional to prevent accidental service disruption

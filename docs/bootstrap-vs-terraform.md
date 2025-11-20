# Bootstrap Script vs Terraform - API Enablement Strategy

## The Problem

You correctly identified a chicken-and-egg problem: Should APIs be enabled in the bootstrap script or in Terraform?

## The Solution

We use a **two-phase approach**:

### Phase 1: Bootstrap Script (Minimal)

**File:** `scripts/setup-platform.sh`

**Enables only these 4 APIs:**
1. `cloudresourcemanager.googleapis.com` - Required for Terraform to manage GCP resources
2. `iam.googleapis.com` - Required for service accounts and IAM bindings
3. `storage.googleapis.com` - Required to create the Terraform state bucket
4. `serviceusage.googleapis.com` - Allows Terraform to enable other APIs

**Why these 4?**
- You literally cannot run Terraform without them
- The state bucket needs `storage.googleapis.com` to exist
- Terraform needs `cloudresourcemanager` and `iam` to do anything useful
- `serviceusage` lets Terraform manage other APIs

### Phase 2: Terraform (Everything Else)

**File:** `platform/terraform/platform-foundation/main.tf`

**Enables all remaining APIs:**
- `compute.googleapis.com` - VPC, networking, compute
- `dns.googleapis.com` - Cloud DNS
- `servicenetworking.googleapis.com` - VPC peering
- `cloudbuild.googleapis.com` - CI/CD
- `artifactregistry.googleapis.com` - Container registry
- `secretmanager.googleapis.com` - Secrets
- `run.googleapis.com` - Cloud Run
- `vpcaccess.googleapis.com` - Serverless VPC Access
- `logging.googleapis.com` - Cloud Logging
- `monitoring.googleapis.com` - Cloud Monitoring

**Why Terraform?**
- ✅ Infrastructure as Code
- ✅ Declarative and versioned
- ✅ Can be reviewed in PRs
- ✅ Consistent with rest of platform
- ✅ Can be destroyed/recreated safely

## Deployment Order

```
1. Bootstrap Script
   └─> Creates: Folder, Project, State Bucket
   └─> Enables: 4 minimal APIs

2. Platform Foundation Terraform
   └─> Enables: All other APIs
   └─> Now VPC/DNS/LB can be deployed

3. Shared VPC Terraform
   └─> Uses: compute.googleapis.com
   └─> Creates: VPC, subnets, NAT

4. DNS Terraform
   └─> Uses: dns.googleapis.com
   └─> Creates: DNS zones

5. Load Balancer Terraform
   └─> Uses: compute.googleapis.com
   └─> Creates: Global LB, SSL
```

## Why Not All APIs in Bootstrap Script?

**Bad:**
```bash
# Enable everything in bash script
gcloud services enable compute.googleapis.com dns.googleapis.com ...
```

**Problems:**
- ❌ Not infrastructure as code
- ❌ No review process
- ❌ No versioning
- ❌ Can't see what changed over time
- ❌ Manual, error-prone

**Good:**
```hcl
# Enable in Terraform
resource "google_project_service" "compute" {
  service = "compute.googleapis.com"
}
```

**Benefits:**
- ✅ Version controlled
- ✅ Can be reviewed in PRs
- ✅ Idempotent (safe to re-run)
- ✅ Self-documenting
- ✅ Consistent with platform philosophy

## Why Not All APIs in Terraform?

Because you can't run Terraform without:
1. A place to store state → needs `storage.googleapis.com`
2. Permission to manage resources → needs `cloudresourcemanager.googleapis.com`
3. Ability to create service accounts → needs `iam.googleapis.com`
4. Ability to enable APIs → needs `serviceusage.googleapis.com`

## Analogy

Think of it like building a house:

**Bootstrap Script** = Pouring the foundation
- Minimum needed to start building
- Done once, manually
- Can't build without it

**Terraform** = Everything else
- All the walls, roof, plumbing, electrical
- Repeatable, version controlled
- Can be modified/rebuilt

## Best Practices

### ✅ DO

- Enable minimal bootstrap APIs in script
- Enable all other APIs in Terraform
- Use `disable_on_destroy = false` for safety
- Document why each API is needed

### ❌ DON'T

- Enable all APIs in bootstrap script
- Mix API enablement between script and Terraform randomly
- Skip the bootstrap APIs (Terraform won't work)
- Use `disable_on_destroy = true` (risky!)

## Verification

After bootstrap script:
```bash
gcloud services list --enabled --project=solvigo-platform-prod
# Should show: storage, iam, cloudresourcemanager, serviceusage
```

After platform-foundation terraform:
```bash
terraform output enabled_services
# Should show: compute, dns, run, secretmanager, etc.
```

## Rollback Safety

If you destroy the `platform-foundation` Terraform:
```bash
cd platform/terraform/platform-foundation
terraform destroy
```

APIs **remain enabled** because `disable_on_destroy = false`.

This prevents accidentally breaking your platform if you destroy the wrong Terraform!

## Summary

| Component | APIs Enabled | Why |
|-----------|-------------|-----|
| **Bootstrap Script** | 4 minimal APIs | Required for Terraform to function |
| **Platform Foundation TF** | 10+ APIs | Infrastructure as Code |
| **Total** | ~14 APIs | Clean separation of concerns |

---

**Result:** Clean, maintainable, infrastructure-as-code approach with minimal manual setup! 🎉

# Solvigo Platform - Architecture Decisions

## Overview
This document records the key architectural decisions made for the Solvigo Platform, which manages multiple client projects on Google Cloud Platform using a hub-and-spoke model with centralized infrastructure.

---

## Decision 1: Domain Structure Pattern

**Decision:** Use hierarchical subdomain pattern: `project.client.solvigo.ai`

**Rationale:**
- Clear visual grouping by client
- Enables wildcard SSL certificates per client (`*.client.solvigo.ai`)
- Better organization in DNS management
- Easier to delegate DNS zones per client if needed in the future

**Examples:**
- `app1.acme-corp.solvigo.ai`
- `dashboard.acme-corp.solvigo.ai`
- `api.techstart.solvigo.ai`

**Implementation Notes:**
- Cloud DNS will have zones per client: `acme-corp.solvigo.ai`
- Global HTTPS Load Balancer will use host-based routing
- SSL certificates: Google-managed certificates with SAN entries for all subdomains

---

## Decision 2: GCP Organization Structure

**Decision:** Use GCP folders - one folder per client

**Structure:**
```
your-organization/
├── solvigo/                          # Company folder
│   ├── solvigo-platform-prod         # Central platform (prod)
│   ├── solvigo-platform-dev          # Central platform (dev)
│   ├── solvigo-shared-services       # Monitoring, logging, etc.
│   │
│   ├── acme-corp/                    # Client folder
│   │   ├── acme-corp-app1-prod
│   │   ├── acme-corp-app1-dev
│   │   └── acme-corp-dashboard-prod
│   │
│   ├── techstart/                    # Another client folder
│   │   ├── techstart-api-prod
│   │   └── techstart-api-dev
│   │
│   └── internal-tools/               # Internal Solvigo projects
│       ├── solvigo-website-prod
│       └── solvigo-crm-prod
```

**Rationale:**
- Scales well as client count grows
- Enables folder-level IAM policies and organization policies
- Clear separation between clients for security and billing
- Supports future delegation (clients can view only their folder)

**Naming Convention:**
- Folders: `{client-name}/`
- Projects: `{client-name}-{project-name}-{env}`
- Environment suffix: `-prod`, `-dev`, `-staging` (optional, based on client choice)

---

## Decision 3: Terraform State Management

**Decision:** One GCS bucket per client

**Structure:**
```
Bucket: {client-name}-terraform-state
├── project1/
│   ├── prod/
│   │   └── default.tfstate
│   └── dev/
│       └── default.tfstate
└── project2/
    └── prod/
        └── default.tfstate

Bucket: solvigo-platform-terraform-state
├── shared-vpc/
│   └── default.tfstate
├── load-balancer/
│   └── default.tfstate
└── cloud-build/
    └── default.tfstate
```

**Rationale:**
- Strong isolation between clients (security and compliance)
- Easier access control per client
- Client-specific state bucket can be in client's billing account
- Simpler to hand off or migrate a client's infrastructure
- Platform infrastructure separate from client infrastructure

**Configuration:**
```hcl
terraform {
  backend "gcs" {
    bucket = "acme-corp-terraform-state"
    prefix = "app1/prod"
  }
}
```

**Bucket Settings:**
- Versioning: Enabled (state history)
- Object lifecycle: Keep last 30 versions
- Location: Same region as primary resources
- IAM: Only project service accounts + platform admin

---

## Decision 4: Environment Strategy

**Decision:** Flexible per client - CLI supports both patterns

**Patterns Supported:**

### Pattern A: Separate Projects Per Environment
```
acme-corp/
├── acme-corp-app1-dev      # Development project
├── acme-corp-app1-staging  # Staging project (optional)
└── acme-corp-app1-prod     # Production project
```
**Best for:** Enterprise clients, strict compliance, high security needs

### Pattern B: Single Project, Multiple Services
```
acme-corp/
└── acme-corp-app1          # One project
    ├── app1-dev            # Cloud Run service
    ├── app1-staging        # Cloud Run service
    └── app1-prod           # Cloud Run service
```
**Best for:** Startups, cost-conscious clients, simple applications

**CLI Behavior:**
```bash
# Pattern A (default for new projects)
solvigo init acme-corp app1 --environments dev,staging,prod

# Pattern B (single project mode)
solvigo init techstart api --single-project --environments dev,prod
```

**Rationale:**
- Flexibility to match client requirements and budget
- Most GCP best practices recommend separate projects (Pattern A)
- Pattern B available for cost optimization
- CLI abstracts complexity of both patterns

---

## Decision 5: Secret Management

**Decision:** Per-project Secret Manager

**Structure:**
```
Project: acme-corp-app1-prod
└── Secret Manager
    ├── database-password
    ├── api-key-stripe
    ├── jwt-secret
    └── oauth-client-secret

Project: solvigo-platform-prod
└── Secret Manager
    ├── github-webhook-secret
    ├── artifact-registry-key
    └── monitoring-api-key
```

**Rationale:**
- Secrets stay with the resources that use them
- No cross-project secret access needed (better security)
- Simpler IAM (Cloud Run service account accesses secrets in same project)
- Easier project hand-off or deletion
- Follows principle of least privilege

**Access Pattern:**
```hcl
# Cloud Run service accesses secret in same project
resource "google_cloud_run_service" "app" {
  # ...
  template {
    spec {
      containers {
        env {
          name = "DATABASE_PASSWORD"
          value_from {
            secret_key_ref {
              name = "database-password"
              key  = "latest"
            }
          }
        }
      }
    }
  }
}
```

**Platform Secrets:**
- Centralized in `solvigo-platform-prod` project
- Only for platform-level operations (CI/CD, monitoring)
- Client projects never access platform secrets

---

## Decision 6: Cost Allocation and Tracking

**Decision:** Mandatory labels on all resources

**Required Labels:**
```hcl
labels = {
  client      = "acme-corp"
  project     = "app1"
  environment = "prod"
  managed_by  = "terraform"
  cost_center = "client-billable"  # or "internal"
}
```

**Label Strategy:**
1. **Applied at project level** (inherited by resources)
2. **Enforced via Organization Policy** (require labels)
3. **Used in billing reports** (filter and group costs)
4. **Terraform module default** (automatically applied)

**Cost Tracking Implementation:**

### 1. GCP Console Billing Reports
- Filter by label: `client=acme-corp`
- Group by: `project` or `environment`
- Export to Sheets for client invoicing

### 2. Billing Export to BigQuery (Optional Future Enhancement)
```sql
-- Example query for client costs
SELECT
  labels.value AS client,
  SUM(cost) AS total_cost
FROM `billing_export.gcp_billing_export`
WHERE labels.key = 'client'
GROUP BY client
ORDER BY total_cost DESC
```

### 3. Budget Alerts
- Set per-project budgets via Terraform
- Alert at 50%, 80%, 100% of budget
- Email notifications to project stakeholders

**Terraform Module Pattern:**
```hcl
# All modules accept standard labels
module "cloud_run_app" {
  source = "../../modules/cloud-run-app"

  labels = merge(
    var.standard_labels,
    {
      component = "backend"
    }
  )
}
```

---

## Summary of Key Implications

### For CLI Tool Development
- Must support both environment patterns (separate projects vs single project)
- Must create GCP folders and set up folder structure
- Must configure per-client GCS buckets for Terraform state
- Must enforce label standards on all created resources
- Must generate DNS entries in hierarchical format

### For Terraform Modules
- All modules must accept `labels` variable
- Backend configuration must support per-client buckets
- Modules must work in both environment patterns
- Secret references must be project-scoped (no cross-project)

### For Central Platform
- Load Balancer must support hierarchical host routing (`*.*.solvigo.ai`)
- DNS must support creating client-specific zones
- Cloud Build must access client-specific state buckets
- IAM must grant access per folder/project hierarchy

### For Operations
- State backups: One bucket per client to backup
- Cost reporting: Filter by `client` label
- Security: Folder-level policies can be applied per client
- Migrations: Each client is self-contained (easier to move)

---

## Implementation Priority

1. **Phase 1: Central Platform**
   - Create `solvigo/` folder structure
   - Set up platform projects
   - Deploy Shared VPC
   - Deploy Global HTTPS Load Balancer with hierarchical host routing
   - Set up Cloud DNS with zone delegation capability

2. **Phase 2: Terraform Modules**
   - Implement standard labels in all modules
   - Create project module (handles folder placement)
   - Create state bucket module (per-client buckets)
   - Build Cloud Run, database, and service backend modules

3. **Phase 3: CLI Tool**
   - Implement folder creation
   - Support both environment patterns
   - Generate state backend configs per client
   - Enforce naming conventions and labels

4. **Phase 4: Validation**
   - Test with one client in both patterns
   - Validate cost tracking with labels
   - Verify DNS and SSL certificate provisioning
   - Test secret access patterns

---

## Open Items for Future Consideration

1. **Multi-region support**: Currently assuming single region, may need multi-region LB routing
2. **Client-specific VPCs**: Some clients may require isolated VPCs (not shared)
3. **Compliance requirements**: HIPAA, SOC2 may require additional controls
4. **Cost attribution**: May need more granular labels (team, feature, etc.)
5. **Disaster recovery**: Cross-region state bucket replication

---

**Document Version:** 1.0
**Last Updated:** 2025-11-17
**Status:** Approved - Ready for Implementation

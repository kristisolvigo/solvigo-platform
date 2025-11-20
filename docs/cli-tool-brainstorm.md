# Solvigo CLI Tool - Brainstorming & Design

**Date:** 2025-11-17
**Status:** Planning Phase

---

## Current State Analysis

### ✅ What We Have
- **Platform Infrastructure:** Fully deployed (Shared VPC, DNS, Load Balancer)
- **One Module:** `gcp-project` (complete, production-ready)
- **Documentation:** Comprehensive architecture decisions and deployment guides
- **Module Placeholders:** Empty directories for 5 additional modules

### 🔄 What We Need
- **CLI Tool:** Python CLI for project scaffolding and management
- **5 More Modules:** Cloud Run, Load Balancer Backend, Databases, State Bucket
- **Import Strategy:** Tool to discover and import existing GCP resources
- **Distribution Method:** How consultants will use the CLI

---

## 1. Automated Subdomain Setup with Load Balancer

### The Challenge
When creating a new client project, we need to:
1. Create DNS zone for client (`client.solvigo.ai`)
2. Create NS record delegation in main zone
3. Create backend service for Cloud Run
4. Register with Load Balancer URL map
5. Create DNS A record pointing to LB IP

### Proposed Solution: Terraform Modules + CLI Orchestration

**Module: `load-balancer-backend`**
```hcl
# modules/load-balancer-backend/main.tf
# This module is called AFTER Cloud Run is deployed

module "lb_backend" {
  source = "../../modules/load-balancer-backend"

  project_id        = "solvigo-platform-prod"
  client_name       = "acme-corp"
  service_name      = "app1"
  cloud_run_url     = module.cloud_run.service_url
  cloud_run_neg     = module.cloud_run.neg_id
  hostnames         = ["app1.acme-corp.solvigo.ai"]

  # Optional
  enable_cdn        = true
  enable_iap        = false
}
```

**What it does:**
1. Creates serverless NEG for Cloud Run service
2. Creates backend service pointing to NEG
3. Updates URL map with new host rule
4. Creates DNS A record in client zone

**CLI handles:**
```bash
solvigo deploy acme-corp app1
# 1. Deploy Cloud Run (module)
# 2. Register with LB (module)
# 3. Wait for SSL cert (if new domain)
# 4. Verify deployment
```

### DNS Zone Creation

**When to create client zone:**
- First project for a client → Create zone
- Additional projects → Reuse existing zone

**CLI logic:**
```python
def ensure_client_dns_zone(client_name):
    # Check if zone exists in platform/terraform/dns/
    if not zone_exists(client_name):
        # Update terraform.tfvars
        add_client_zone(client_name)
        # Run terraform apply
        terraform_apply("platform/terraform/dns")
```

**Result:**
- `acme-corp.solvigo.ai` zone created
- NS records auto-delegated from main zone
- Ready for project-specific A records

---

## 2. CLI Distribution Strategy

### Option A: Git Submodule (❌ Not Recommended)

**How it works:**
```bash
# In client project repo
git submodule add https://github.com/solvigo/platform.git .solvigo-platform
.solvigo-platform/cli/solvigo init
```

**Pros:**
- Version pinning per project
- Clear separation

**Cons:**
- ❌ Submodules are complex and error-prone
- ❌ Consultants need to update submodules manually
- ❌ Different versions across projects = support nightmare
- ❌ Extra cognitive load

### Option B: Local Editable Install (✅ **RECOMMENDED**)

**Setup (one-time per consultant):**
```bash
# Clone platform repo
cd ~/solvigo/
git clone <platform-repo> solvigo-platform
cd solvigo-platform/cli
pip install -e .

# Now `solvigo` command available globally
solvigo --version
```

**From any project:**
```bash
cd ~/client-projects/acme-corp/
solvigo init acme-corp app1
solvigo deploy
```

**Pros:**
- ✅ One version for all consultants (easy updates)
- ✅ Simple: just `git pull` to update
- ✅ No per-project setup
- ✅ Works from anywhere

**Cons:**
- Different consultant machines might have different versions
- Solution: Pin version in platform repo, CI/CD checks

### Option C: Internal PyPI Package (Future Enhancement)

**Setup:**
```bash
pip install solvigo-cli --index-url https://pypi.solvigo.internal
```

**Pros:**
- ✅ Professional distribution
- ✅ Version management via pip
- ✅ Easy updates: `pip install --upgrade`

**Cons:**
- Requires internal PyPI server setup
- Overkill for small team

### **Recommendation: Option B (Local Editable Install)**

**Why:**
- Simple for 5-10 person team
- Easy to update (git pull)
- No infrastructure needed
- Can upgrade to Option C later if needed

**CLI Structure:**
```
cli/
├── setup.py
├── solvigo/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── commands/
│   │   ├── init.py          # solvigo init
│   │   ├── import.py        # solvigo import
│   │   ├── deploy.py        # solvigo deploy
│   │   └── status.py        # solvigo status
│   ├── terraform/
│   │   ├── runner.py        # Terraform wrapper
│   │   └── state.py         # State management
│   ├── gcp/
│   │   ├── discovery.py     # Resource discovery
│   │   └── iam.py           # IAM helpers
│   └── templates/           # Cookiecutter templates
│       ├── cloud-run/
│       └── fastapi/
└── README.md
```

---

## 3. Finding & Importing Existing Resources

### Strategy: Three-Tier Approach

#### Tier 1: Discovery (Automated)
**CLI scans GCP project and lists resources:**

```bash
solvigo discover acme-corp-app1-prod

# Output:
Found resources in acme-corp-app1-prod:
  Cloud Run Services:
    - app1-frontend (europe-north1)
    - app1-backend (europe-north1)

  Cloud SQL Instances:
    - app1-db (PostgreSQL 15, europe-north1)

  Storage Buckets:
    - acme-corp-app1-uploads
    - acme-corp-app1-static

  Secret Manager Secrets:
    - database-password
    - api-key-stripe

  VPC Connectors:
    - serverless-vpc-connector
```

**Implementation:**
```python
# solvigo/gcp/discovery.py
def discover_resources(project_id):
    resources = {
        'cloud_run': list_cloud_run_services(project_id),
        'cloud_sql': list_cloud_sql_instances(project_id),
        'buckets': list_storage_buckets(project_id),
        'secrets': list_secrets(project_id),
    }
    return resources
```

#### Tier 2: Generate Import Code (Semi-Automated)

```bash
solvigo import acme-corp-app1-prod --resource cloud-run/app1-frontend

# Generates:
# clients/acme-corp/app1/terraform/imports.tf
import {
  to = module.frontend.google_cloud_run_service.service
  id = "locations/europe-north1/namespaces/acme-corp-app1-prod/services/app1-frontend"
}

# Also generates module configuration:
module "frontend" {
  source = "../../../../modules/cloud-run-app"

  service_name = "app1-frontend"
  # ... detected configuration
}
```

**Tools to use:**
1. **gcloud CLI** - List resources
2. **Terraform import blocks** - Import into state
3. **Terraformer** (optional) - Auto-generate configs

#### Tier 3: Manual Review & Cleanup

**CLI generates, human reviews:**
```bash
solvigo import acme-corp-app1-prod --all --dry-run > import-plan.txt

# Human reviews import-plan.txt
# Edits generated terraform
# Then:

solvigo import acme-corp-app1-prod --all --apply
```

### Import Priority Order

**High Priority (Phase 1):**
1. ✅ Cloud Run services
2. ✅ Cloud SQL databases
3. ✅ Storage buckets
4. ✅ Secret Manager secrets

**Medium Priority (Phase 2):**
5. VPC connectors
6. Service accounts
7. IAM bindings
8. Cloud Build triggers

**Low Priority (Future):**
9. Monitoring/alerting
10. Logging sinks
11. Custom IAM roles

### Example Import Workflow

```bash
# Step 1: Discover what exists
solvigo discover existing-project-123

# Step 2: Choose what to import
solvigo import existing-project-123 \
  --resources cloud-run,cloud-sql,secrets \
  --client acme-corp \
  --project legacy-app

# Step 3: CLI does:
# - Creates clients/acme-corp/legacy-app/ structure
# - Generates Terraform modules
# - Creates import blocks
# - Runs terraform plan (shows what will be imported)

# Step 4: Human reviews
vim clients/acme-corp/legacy-app/terraform/main.tf

# Step 5: Apply import
cd clients/acme-corp/legacy-app/terraform
terraform init
terraform plan  # Should show no changes (already imported)
terraform apply
```

---

## 4. Handling Existing Projects

### Scenario A: Existing Project, Needs Organization

**Before:**
```
GCP Project: random-project-123 (in random org location)
Resources: Cloud Run, Cloud SQL, secrets scattered
No Terraform, no structure
```

**After CLI:**
```
solvigo migrate random-project-123 --client acme-corp --project legacy-app

# Creates:
clients/acme-corp/legacy-app/
├── terraform/
│   ├── main.tf          # Imported resources
│   ├── imports.tf       # Import blocks
│   └── backend.tf       # State bucket config
├── app/
│   ├── frontend/        # Code (if we manage it)
│   └── backend/
└── cloudbuild.yaml
```

**CLI Steps:**
1. ✅ Create client folder if doesn't exist
2. ✅ Create GCS state bucket for client
3. ✅ Discover existing resources
4. ✅ Generate Terraform configs
5. ✅ Import into Terraform state
6. ⚠️ Optionally: Move project to correct GCP folder
7. ⚠️ Optionally: Attach to Shared VPC (if possible)

**Project Movement:**
```bash
# Moving GCP project to correct folder
gcloud projects move random-project-123 --folder=folders/212465532368/acme-corp

# Renaming (can't rename, must create new)
# For existing projects, keep old name, document in terraform
```

### Scenario B: New Project, Existing Client

**Simple:**
```bash
solvigo init acme-corp new-dashboard

# Uses existing client folder and DNS zone
clients/acme-corp/
├── app1/           # Existing
└── new-dashboard/  # New (CLI creates)
```

### Scenario C: Brand New Client + Project

**Full setup:**
```bash
solvigo init techstart api --new-client

# Creates:
# 1. GCP folder: solvigo/techstart/
# 2. DNS zone: techstart.solvigo.ai
# 3. State bucket: techstart-terraform-state
# 4. First project: techstart-api-prod (or dev, or both)
# 5. Cloud Run + LB registration
```

---

## 5. Setting Up New Projects Altogether

### Interactive CLI Design (✅ **RECOMMENDED**)

The CLI should be **interactive** and **context-aware**, guiding consultants through the setup process.

### User Experience Flow

**Scenario 1: Running from Existing Project Directory**

```bash
$ cd clients/acme-corp/app1/
$ solvigo

╔══════════════════════════════════════════════════════════════╗
║          🚀 Welcome to Solvigo CLI v1.0.0                    ║
╚══════════════════════════════════════════════════════════════╝

📂 Project detected: acme-corp/app1
   Location: clients/acme-corp/app1/

What would you like to do?

  1. Continue with existing project
  2. Create new project
  3. Choose different existing project
  4. Import existing GCP project

→ Enter choice (1-4):
```

**Scenario 2: Running from Root or Unknown Directory**

```bash
$ cd ~/solvigo-platform/
$ solvigo

╔══════════════════════════════════════════════════════════════╗
║          🚀 Welcome to Solvigo CLI v1.0.0                    ║
╚══════════════════════════════════════════════════════════════╝

No project detected in current directory.

What would you like to do?

  1. Create new project
  2. Choose existing project
  3. Import existing GCP project
  4. Setup new client

→ Enter choice (1-4):
```

**What it does:**

#### Step 1: Pre-checks
```
✓ Checking GCP authentication
✓ Checking billing permissions
✓ Verifying platform infrastructure
✓ Checking if client exists
```

#### Step 2: Project Creation
```
→ Creating GCP folder (if new client)
→ Creating DNS zone (if new client)
→ Creating state bucket (if new client)
→ Creating GCP project: acme-corp-dashboard-prod
→ Attaching to Shared VPC
→ Creating directory structure
```

#### Step 3: Infrastructure Generation
```
→ Generating Terraform configs
→ Configuring backend (state bucket)
→ Creating Cloud Run module config
→ Creating database module config (if --database)
→ Creating LB backend registration
```

#### Step 4: Code Scaffolding (Optional)
```
→ Generating React + Vite frontend (if --stack frontend or fullstack)
→ Generating FastAPI backend (if --stack backend or fullstack)
→ Creating Dockerfile
→ Creating Cloud Build config
```

#### Step 5: Initial Deployment
```
→ Initializing Terraform
→ Planning infrastructure
→ Applying (with confirmation)
→ Registering with Load Balancer
→ Creating DNS records
```

**Final Output:**
```
✓ Project created successfully!

  Project ID: acme-corp-dashboard-prod
  URL:        https://dashboard.acme-corp.solvigo.ai

  Next steps:
  1. Wait for SSL certificate (~10 min)
  2. Push code to trigger Cloud Build
  3. Monitor: gcloud run services describe ...

  Location: clients/acme-corp/dashboard/
```

### CLI Command Design

```python
# solvigo/commands/init.py

@click.command()
@click.argument('client')
@click.argument('project')
@click.option('--env', default='prod', help='Environment (dev/staging/prod)')
@click.option('--stack', type=click.Choice(['frontend', 'backend', 'fullstack']), default='fullstack')
@click.option('--database', type=click.Choice(['none', 'firestore', 'postgres']), default='none')
@click.option('--new-client', is_flag=True, help='This is a new client')
@click.option('--no-deploy', is_flag=True, help='Generate only, don\'t deploy')
def init(client, project, env, stack, database, new_client, no_deploy):
    """Create a new client project with full infrastructure setup."""

    # Validation
    validate_naming(client, project)
    check_prerequisites()

    # Client setup
    if new_client or not client_exists(client):
        create_client_structure(client)
        create_dns_zone(client)
        create_state_bucket(client)

    # Project setup
    project_id = f"{client}-{project}-{env}"
    create_project_directory(client, project, env)

    # Terraform generation
    generate_terraform_config(client, project, env, stack, database)

    # Code scaffolding
    if stack in ['frontend', 'fullstack']:
        scaffold_frontend(client, project)
    if stack in ['backend', 'fullstack']:
        scaffold_backend(client, project)

    # Deployment
    if not no_deploy:
        deploy_infrastructure(client, project, env)
        register_load_balancer(client, project)
        create_dns_records(client, project)

    print_success_message(client, project, env)
```

---

## 6. Billing Management Strategy

### The Challenge
- Only you and CEO have billing admin access
- Creating projects requires linking billing account
- Security concern: Don't want consultants having billing admin

### Option A: Manual Billing Link (✅ **RECOMMENDED for now**)

**CLI creates project WITHOUT billing:**
```python
gcloud projects create acme-corp-app1-prod \
  --folder=folders/212465532368 \
  --labels=client=acme-corp,environment=prod

# No --billing-account flag
```

**Then notify admin:**
```
✓ Project created: acme-corp-app1-prod
⚠ Billing account not linked (requires admin)

ACTION REQUIRED:
  You or CEO must run:
  gcloud billing projects link acme-corp-app1-prod \
    --billing-account=XXXXXX-XXXXXX-XXXXXX
```

**Pros:**
- ✅ Secure (consultants can't rack up bills)
- ✅ Manual approval for each project
- ✅ Simple implementation

**Cons:**
- ❌ Bottleneck (requires admin intervention)
- ❌ Delays deployment

### Option B: Service Account with Billing Role (⚠️ **More Automated**)

**Create dedicated service account:**
```bash
# As billing admin, create service account
gcloud iam service-accounts create solvigo-project-creator \
  --display-name="Solvigo Project Creator" \
  --project=solvigo-platform-prod

# Grant minimum billing permission
gcloud organizations add-iam-policy-binding 587347368878 \
  --member="serviceAccount:solvigo-project-creator@solvigo-platform-prod.iam.gserviceaccount.com" \
  --role="roles/billing.projectManager"

# Also needs project creator role
gcloud organizations add-iam-policy-binding 587347368878 \
  --member="serviceAccount:solvigo-project-creator@solvigo-platform-prod.iam.gserviceaccount.com" \
  --role="roles/resourcemanager.projectCreator"
```

**IAM Role: `roles/billing.projectManager`**
- Can link **existing** billing accounts to projects
- **Cannot** create new billing accounts
- **Cannot** modify billing account settings
- **Cannot** view billing data

**CLI uses service account:**
```python
# CLI authenticates as service account
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/path/to/sa-key.json'

# Creates project AND links billing
gcloud projects create acme-corp-app1-prod \
  --billing-account=$SOLVIGO_BILLING_ACCOUNT
```

**Pros:**
- ✅ Fully automated project creation
- ✅ No admin bottleneck
- ✅ Service account can't create billing accounts
- ✅ Audit trail (all actions attributed to SA)

**Cons:**
- ⚠️ Service account key must be secured
- ⚠️ Consultants could create many projects (cost risk)
- ⚠️ Less oversight

### Option C: Hybrid Approach (✅ **BEST BALANCE**)

**For new projects:**
1. CLI creates project WITHOUT billing
2. Sends Slack notification to admins
3. Admin approves + links billing via Slack command
4. CLI polls for billing link, continues when ready

**For existing/imported projects:**
- Already have billing, no action needed

**Implementation:**
```python
# solvigo/commands/init.py

def create_project(client, project, env):
    project_id = create_gcp_project(client, project, env)

    if config.AUTO_LINK_BILLING:
        # Option B: Use service account
        link_billing_automated(project_id)
    else:
        # Option A: Manual approval
        send_billing_approval_request(project_id)
        wait_for_billing_link(project_id, timeout=300)  # 5 min

    return project_id
```

**Slack Integration (Future):**
```
🔔 New Project Approval Request

Client: acme-corp
Project: dashboard-prod
Created by: kristi.francis@solvigo.ai

[Approve & Link Billing] [Deny]
```

### **Recommendation: Start with Option A, Upgrade to Option C**

**Phase 1 (Now):**
- Manual billing link
- Simple and secure
- Works for 1-2 projects/week

**Phase 2 (Later):**
- Add Slack notifications
- Add approval workflow
- Reduces admin overhead

**Phase 3 (Future):**
- Service account for approved clients
- Automated for trusted consultants
- Manual approval for large/expensive projects

---

## Implementation Roadmap

### Week 1-2: Core CLI + Cloud Run Module
- [ ] CLI project structure (setup.py, entry point)
- [ ] `solvigo init` basic scaffolding
- [ ] Cloud Run module (Terraform)
- [ ] Load Balancer Backend module
- [ ] Test: Deploy one Cloud Run service end-to-end

### Week 3-4: Import Functionality
- [ ] GCP resource discovery (gcloud wrapper)
- [ ] Import code generation
- [ ] `solvigo import` command
- [ ] Test: Import existing project

### Week 5-6: Templates & Polish
- [ ] React + Vite template
- [ ] FastAPI template
- [ ] Database modules (Firestore, Cloud SQL)
- [ ] Documentation
- [ ] Test: Full new project creation

### Week 7-8: Production Hardening
- [ ] Error handling
- [ ] Validation
- [ ] Rollback capabilities
- [ ] Logging and audit trail
- [ ] Team onboarding

---

## Open Questions for Discussion

1. **Billing Approval:** Start manual or invest in service account automation?
2. **CLI Distribution:** Editable install good enough, or need internal package?
3. **Import Scope:** Which resource types are highest priority?
4. **Code Management:** Should CLI also scaffold application code, or just infrastructure?
5. **Testing:** How to test CLI without creating real GCP resources?
6. **Multi-region:** Always Stockholm, or support multi-region deployments?

---

**Next Steps:**
1. Review this document
2. Decide on billing approach
3. Prioritize module development order
4. Start CLI skeleton with `solvigo init` command

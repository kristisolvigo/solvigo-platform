# Solvigo Platform

A centralized platform for managing multiple client projects on Google Cloud Platform using a hub-and-spoke architecture with shared infrastructure and automated project scaffolding.

## 🏗️ Architecture

- **Hub-and-Spoke**: Central platform with Shared VPC connecting to client service projects
- **Global HTTPS Load Balancer**: Single entry point routing to all client services
- **Hierarchical DNS**: `project.client.solvigo.ai` domain structure
- **Per-Client Isolation**: Separate GCP folders, projects, and state buckets per client
- **Automated Scaffolding**: CLI tool for creating new projects with best practices

## 📋 Features

### Central Platform
- ✅ Shared VPC (host project)
- ✅ Global HTTPS Load Balancer with SSL
- ✅ Cloud DNS with zone delegation
- ✅ Centralized Cloud Build (CI/CD)
- ✅ Artifact Registry for Docker images

### Client Projects
- ✅ Auto-generated GCP projects with proper labeling
- ✅ React + Vite frontend templates
- ✅ FastAPI backend templates
- ✅ Cloud Run deployment
- ✅ Firestore or Cloud SQL databases
- ✅ Secret Manager integration
- ✅ Flexible environments (dev/staging/prod)

### CLI Tool (Coming Soon)
- `solvigo init` - Create new client project
- `solvigo import` - Import existing infrastructure
- `solvigo deploy` - Trigger CI/CD deployment
- `solvigo status` - View all client projects

## 🚀 Quick Start

### Prerequisites

- GCP Organization with billing enabled
- Organization Admin or Folder Admin permissions
- Domain name (e.g., `solvigo.ai`)
- Tools installed:
  - [gcloud CLI](https://cloud.google.com/sdk/docs/install)
  - [Terraform](https://www.terraform.io/downloads) >= 1.5.0
  - Git

### Step 1: Platform Setup

Run the automated setup script:

```bash
# Clone the repository
git clone <your-repo-url>
cd create-app

# Run platform setup
./scripts/setup-platform.sh
```

This will:
1. Create GCP folder structure
2. Create `solvigo-platform-prod` project
3. Enable required APIs
4. Create Terraform state bucket

After completion, source the configuration:

```bash
source .solvigo_config
```

### Step 2: Enable Platform APIs

```bash
cd platform/terraform/platform-foundation
terraform init
terraform apply
```

This enables all required GCP APIs (Compute, DNS, Cloud Run, etc.) via Terraform.

### Step 3: Deploy Shared VPC

```bash
cd ../shared-vpc
terraform init
terraform plan
terraform apply
```

This creates:
- Shared VPC network
- Subnets in `europe-north2` (Stockholm) and `europe-north1` (Finland)
- Cloud NAT for outbound internet
- Firewall rules

### Step 4: Deploy Cloud DNS

```bash
cd ../dns
terraform init

# Edit terraform.tfvars (or pass variables)
# Add your client zones
terraform apply -var='client_zones={"acme-corp"={description="ACME Corp"}}'
```

**Important**: After apply, get the name servers:

```bash
terraform output main_zone_name_servers
```

Configure these name servers at your domain registrar (e.g., Google Domains, Namecheap).

### Step 5: Deploy Load Balancer

```bash
cd ../load-balancer
terraform init
terraform plan
terraform apply
```

Get the load balancer IP:

```bash
terraform output load_balancer_ip
```

**Note**: SSL certificate will provision after DNS propagates (~10-30 minutes).

### Step 5: Create Your First Client Project

Coming soon: Use the CLI tool. For now, see the manual example below.

## 📂 Repository Structure

```
solvigo-platform/
├── platform/                   # Central platform infrastructure
│   ├── terraform/
│   │   ├── platform-foundation/ # ✅ API enablement
│   │   ├── shared-vpc/         # ✅ Shared VPC configuration
│   │   ├── dns/                # ✅ Cloud DNS zones
│   │   ├── load-balancer/      # ✅ Global HTTPS LB
│   │   └── cloud-build/        # ✅ Central CI/CD (GitHub connection)
│   └── modules/                # ✅ Platform infrastructure modules
│       └── cloud-build-pipeline/ # ✅ CI/CD setup (per-client)
├── modules/                    # Client application modules (CLI uses these)
│   ├── gcp-project/            # ✅ Project creation module
│   ├── service-account/        # ✅ Service account module
│   ├── cloud-run-app/          # ✅ Cloud Run service
│   ├── load-balancer-backend/  # ✅ LB backend registration
│   ├── database-firestore/     # ✅ Firestore setup
│   ├── database-cloudsql/      # ✅ Cloud SQL setup
│   └── storage-bucket/         # ✅ Storage bucket
├── clients/                    # Client project configurations
│   └── <client-name>/
│       └── <project-name>/
│           ├── terraform/      # Infrastructure as code
│           ├── app/            # Application code
│           └── cloudbuild.yaml # CI/CD configuration
├── scripts/                    # Helper scripts
│   └── setup-platform.sh       # ✅ Platform setup automation
├── docs/                       # Documentation
│   ├── architecture-decisions.md  # ✅ ADR document
│   └── implementation-guide.md    # ✅ Detailed guide
└── cli/                        # 🔄 Python CLI tool (coming soon)
```

## 🏢 GCP Organization Structure

```
your-organization/
└── solvigo/                       # Main folder
    ├── solvigo-platform-prod      # Central platform
    ├── acme-corp/                 # Client folder
    │   ├── acme-corp-app1-prod
    │   ├── acme-corp-app1-dev
    │   └── acme-corp-dashboard-prod
    └── techstart/                 # Another client
        ├── techstart-api-prod
        └── techstart-api-dev
```

## 🌐 Domain Structure

```
solvigo.ai
├── acme-corp.solvigo.ai
│   ├── app1.acme-corp.solvigo.ai      → Cloud Run service
│   └── dashboard.acme-corp.solvigo.ai → Cloud Run service
└── techstart.solvigo.ai
    ├── api.techstart.solvigo.ai       → Cloud Run service
    └── web.techstart.solvigo.ai       → Cloud Run service
```

## 📖 Documentation

### Guides
- **[Quick Start](QUICKSTART.md)** - Get started in 5 minutes
- **[Deployment Checklist](docs/deployment-checklist.md)** - Step-by-step deployment guide
- **[Implementation Guide](docs/implementation-guide.md)** - Detailed deployment steps
- **[Architecture Decisions](docs/architecture-decisions.md)** - Key architectural choices and rationale
- **[Environment Strategy](docs/environment-strategy.md)** - Staging + Prod approach
- **[Reference Architecture](docs/reference-architecture-patterns.md)** - Proven patterns from registry-api

### Technical Guides
- **[CI/CD Setup](docs/cicd-setup-guide.md)** - Cloud Build configuration
- **[CLI Implementation](docs/cli-implementation-status.md)** - CLI tool features
- **[CLI Flows](docs/cli-interactive-flows.md)** - Interactive workflows
- **[Module Organization](docs/module-organization.md)** - Module structure

### Module Documentation
- [GCP Project Module](modules/gcp-project/README.md)
- [Shared VPC](platform/terraform/shared-vpc/)
- [Cloud DNS](platform/terraform/dns/README.md)
- [Load Balancer](platform/terraform/load-balancer/README.md)

## 🔧 Manual Client Project Example

Until the CLI tool is ready, here's how to create a client project manually:

### 1. Create Client Folder in GCP

```bash
export CLIENT_NAME="acme-corp"
gcloud resource-manager folders create \
  --display-name="$CLIENT_NAME" \
  --folder=$(cat .solvigo_folder_id)
```

### 2. Create Client Directory

```bash
mkdir -p clients/$CLIENT_NAME/app1/terraform
cd clients/$CLIENT_NAME/app1/terraform
```

### 3. Create Terraform Configuration

**main.tf**:
```hcl
terraform {
  backend "gcs" {
    bucket = "acme-corp-terraform-state"
    prefix = "app1/prod"
  }
}

provider "google" {
  region = "us-central1"
}

# Get client folder ID
data "google_folder" "client" {
  folder = "folders/${var.solvigo_folder_id}"
  filter = "displayName:${var.client_name}"
}

# Create project
module "project" {
  source = "../../../../modules/gcp-project"

  client_name        = var.client_name
  project_name       = "app1"
  environment        = "prod"
  folder_id          = data.google_folder.client.name
  billing_account_id = var.billing_account_id
}

# TODO: Add Cloud Run, database, load balancer backend modules
```

**variables.tf**:
```hcl
variable "client_name" {
  default = "acme-corp"
}

variable "solvigo_folder_id" {
  description = "Main Solvigo folder ID"
}

variable "billing_account_id" {
  description = "Billing account ID"
}
```

### 4. Deploy

```bash
terraform init
terraform apply \
  -var="solvigo_folder_id=$(cat ../../../../.solvigo_folder_id)" \
  -var="billing_account_id=$SOLVIGO_BILLING_ACCOUNT"
```

## 💰 Cost Tracking

All resources are labeled for cost allocation:

```hcl
labels = {
  client      = "acme-corp"
  project     = "app1"
  environment = "prod"
  managed_by  = "terraform"
  cost_center = "client-billable"
}
```

View costs by client in GCP Console → Billing → Reports → Group by: `client` label

## 🔐 Security

- **Shared VPC**: Network isolation between clients
- **IAM**: Least-privilege service accounts per project
- **Secret Manager**: Secrets stay in client projects
- **DNSSEC**: Enabled on all DNS zones
- **HTTPS**: Managed SSL certificates with automatic renewal
- **Firewall Rules**: Default deny, explicit allow

## 🚦 Deployment Status

### Platform Infrastructure
- ✅ Shared VPC
- ✅ Cloud DNS
- ✅ Global Load Balancer
- 🔄 Cloud Build (planned)
- 🔄 Artifact Registry (planned)

### Terraform Modules
- ✅ GCP Project
- 🔄 Cloud Run App (planned)
- 🔄 Load Balancer Backend (planned)
- 🔄 Database - Firestore (planned)
- 🔄 Database - Cloud SQL (planned)

### Tooling
- ✅ Platform setup script
- 🔄 Python CLI tool (in development)

## 🤝 Contributing

This is an internal Solvigo project. For consultants:

1. Follow the established patterns in `modules/`
2. All resources must have proper labels
3. Use the `gcp-project` module for new projects
4. Document any new modules with README.md
5. Test changes in dev environment first

## 📞 Support

For questions or issues:
- Check the `/docs` folder for detailed guides
- Review existing client projects in `/clients` for examples
- Contact the platform team

## 🗺️ Roadmap

### Phase 1: Core Platform ✅
- [x] Shared VPC
- [x] Cloud DNS
- [x] Global Load Balancer
- [x] GCP Project module
- [x] Platform setup script

### Phase 2: Modules (In Progress)
- [ ] Cloud Run App module
- [ ] Load Balancer Backend module
- [ ] Database modules (Firestore, Cloud SQL)
- [ ] Frontend template (React + Vite)
- [ ] Backend template (FastAPI)

### Phase 3: CI/CD
- [ ] Central Cloud Build configuration
- [ ] Docker build triggers
- [ ] Automated Cloud Run deployment
- [ ] Environment promotion workflows

### Phase 4: CLI Tool
- [ ] `solvigo init` - Project scaffolding
- [ ] `solvigo import` - Import existing infra
- [ ] `solvigo deploy` - Trigger deployments
- [ ] `solvigo status` - View all projects

### Phase 5: Operations
- [ ] Monitoring dashboards
- [ ] Log aggregation
- [ ] Cost reporting
- [ ] Backup automation

## 📄 License

Internal use only - Solvigo proprietary.

---

**Built with ❤️ by the Solvigo Platform Team**

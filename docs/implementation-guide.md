# Solvigo Platform - Implementation Guide

Based on the architectural decisions made, this guide provides concrete next steps for implementation.

---

## Prerequisites

Before starting implementation, ensure you have:

- [ ] GCP Organization with billing enabled
- [ ] Organization Admin or Folder Admin permissions
- [ ] Domain `solvigo.ai` registered and DNS managed in GCP (or transferable)
- [ ] Terraform >= 1.5.0 installed
- [ ] gcloud CLI installed and authenticated
- [ ] Git repository initialized (✅ already done)

---

## Phase 1: Central Platform Setup

### Step 1.1: Create GCP Folder Structure

```bash
# Set your organization ID
export ORG_ID="your-org-id"

# Create main Solvigo folder
gcloud resource-manager folders create \
  --display-name="solvigo" \
  --organization=${ORG_ID}

# Get the folder ID (save this!)
export SOLVIGO_FOLDER_ID=$(gcloud resource-manager folders list \
  --organization=${ORG_ID} \
  --filter="displayName:solvigo" \
  --format="value(name)")

echo "Solvigo Folder ID: ${SOLVIGO_FOLDER_ID}"
```

### Step 1.2: Create Platform Projects

```bash
# Create platform production project
gcloud projects create solvigo-platform-prod \
  --folder=${SOLVIGO_FOLDER_ID} \
  --name="Solvigo Platform (Production)" \
  --labels=environment=prod,managed_by=terraform,cost_center=internal

# Link billing account
gcloud billing projects link solvigo-platform-prod \
  --billing-account=YOUR_BILLING_ACCOUNT_ID

# Enable required APIs
gcloud services enable compute.googleapis.com \
  dns.googleapis.com \
  cloudresourcemanager.googleapis.com \
  servicenetworking.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  --project=solvigo-platform-prod
```

### Step 1.3: Set Up Terraform State Bucket (Platform)

```bash
# Create state bucket for platform infrastructure
gcloud storage buckets create gs://solvigo-platform-terraform-state \
  --project=solvigo-platform-prod \
  --location=europe-north2 \
  --uniform-bucket-level-access

# Enable versioning
gcloud storage buckets update gs://solvigo-platform-terraform-state \
  --versioning
```

### Step 1.4: Initialize Platform Terraform

**Directory Structure:**
```
platform/
├── terraform/
│   ├── shared-vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── backend.tf
│   ├── load-balancer/
│   ├── cloud-build/
│   └── dns/
```

**Start with Shared VPC:**

Create `platform/terraform/shared-vpc/backend.tf`:
```hcl
terraform {
  backend "gcs" {
    bucket = "solvigo-platform-terraform-state"
    prefix = "shared-vpc"
  }

  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}
```

Create `platform/terraform/shared-vpc/main.tf`:
```hcl
provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  standard_labels = {
    managed_by  = "terraform"
    environment = "prod"
    cost_center = "internal"
    component   = "networking"
  }
}

# Create VPC Network (Host Project)
resource "google_compute_network" "shared_vpc" {
  name                    = "solvigo-shared-vpc"
  auto_create_subnetworks = false
  routing_mode           = "GLOBAL"

  project = var.project_id
}

# Enable VPC Host Project
resource "google_compute_shared_vpc_host_project" "host" {
  project = var.project_id
}

# Create Subnets per Region
resource "google_compute_subnetwork" "subnets" {
  for_each = var.subnets

  name          = each.value.name
  ip_cidr_range = each.value.cidr
  region        = each.value.region
  network       = google_compute_network.shared_vpc.id

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }

  project = var.project_id
}

# Cloud Router for NAT (per region)
resource "google_compute_router" "router" {
  for_each = toset([for s in var.subnets : s.region])

  name    = "solvigo-router-${each.key}"
  region  = each.key
  network = google_compute_network.shared_vpc.id

  project = var.project_id
}

# Cloud NAT (per region)
resource "google_compute_router_nat" "nat" {
  for_each = toset([for s in var.subnets : s.region])

  name   = "solvigo-nat-${each.key}"
  router = google_compute_router.router[each.key].name
  region = each.key

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }

  project = var.project_id
}
```

Create `platform/terraform/shared-vpc/variables.tf`:
```hcl
variable "project_id" {
  description = "GCP Project ID for platform"
  type        = string
  default     = "solvigo-platform-prod"
}

variable "region" {
  description = "Default GCP region"
  type        = string
  default     = "europe-north2"
}

variable "subnets" {
  description = "Subnets to create in Shared VPC"
  type = list(object({
    name   = string
    cidr   = string
    region = string
  }))

  default = [
    {
      name   = "solvigo-subnet-europe-north2"
      cidr   = "10.0.0.0/20"
      region = "europe-north2"
    },
    {
      name   = "solvigo-subnet-europe-north1"
      cidr   = "10.0.16.0/20"
      region = "europe-north1"
    }
  ]
}
```

Create `platform/terraform/shared-vpc/outputs.tf`:
```hcl
output "network_id" {
  description = "Shared VPC network ID"
  value       = google_compute_network.shared_vpc.id
}

output "network_self_link" {
  description = "Shared VPC network self link"
  value       = google_compute_network.shared_vpc.self_link
}

output "subnet_ids" {
  description = "Map of subnet names to IDs"
  value = {
    for k, v in google_compute_subnetwork.subnets : k => v.id
  }
}
```

### Step 1.5: Deploy Shared VPC

```bash
cd platform/terraform/shared-vpc
terraform init
terraform plan
terraform apply
```

---

## Phase 2: Create Reusable Terraform Modules

### Module Structure

```
modules/
├── gcp-project/           # Creates GCP project with folder, billing, APIs
├── cloud-run-app/         # Cloud Run service with VPC connector, IAM
├── load-balancer-backend/ # Registers service with central LB
├── database-firestore/    # Firestore database setup
├── database-cloudsql/     # Cloud SQL PostgreSQL setup
└── terraform-state-bucket/ # Creates per-client state bucket
```

### Module 1: GCP Project Module

Create `modules/gcp-project/main.tf`:
```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

locals {
  project_id = "${var.client_name}-${var.project_name}${var.environment != "" ? "-${var.environment}" : ""}"

  standard_labels = {
    client      = var.client_name
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
    cost_center = "client-billable"
  }

  labels = merge(local.standard_labels, var.additional_labels)
}

# Create GCP Project
resource "google_project" "project" {
  name            = local.project_id
  project_id      = local.project_id
  folder_id       = var.folder_id
  billing_account = var.billing_account_id
  labels          = local.labels
}

# Enable required APIs
resource "google_project_service" "services" {
  for_each = toset(var.enabled_apis)

  project = google_project.project.project_id
  service = each.key

  disable_on_destroy = false
}

# Attach to Shared VPC as Service Project
resource "google_compute_shared_vpc_service_project" "service" {
  count = var.attach_to_shared_vpc ? 1 : 0

  host_project    = var.shared_vpc_host_project
  service_project = google_project.project.project_id

  depends_on = [google_project_service.services]
}
```

Create `modules/gcp-project/variables.tf`:
```hcl
variable "client_name" {
  description = "Client name (lowercase, hyphens)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.client_name))
    error_message = "Client name must be lowercase alphanumeric with hyphens only"
  }
}

variable "project_name" {
  description = "Project name (lowercase, hyphens)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must be lowercase alphanumeric with hyphens only"
  }
}

variable "environment" {
  description = "Environment (dev, staging, prod, or empty for single-project mode)"
  type        = string
  default     = ""
}

variable "folder_id" {
  description = "GCP Folder ID where project will be created"
  type        = string
}

variable "billing_account_id" {
  description = "GCP Billing Account ID"
  type        = string
}

variable "enabled_apis" {
  description = "List of GCP APIs to enable"
  type        = list(string)
  default = [
    "compute.googleapis.com",
    "run.googleapis.com",
    "vpcaccess.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ]
}

variable "attach_to_shared_vpc" {
  description = "Whether to attach project to Shared VPC"
  type        = bool
  default     = true
}

variable "shared_vpc_host_project" {
  description = "Shared VPC host project ID"
  type        = string
  default     = "solvigo-platform-prod"
}

variable "additional_labels" {
  description = "Additional labels to apply"
  type        = map(string)
  default     = {}
}
```

Create `modules/gcp-project/outputs.tf`:
```hcl
output "project_id" {
  description = "GCP Project ID"
  value       = google_project.project.project_id
}

output "project_number" {
  description = "GCP Project Number"
  value       = google_project.project.number
}

output "labels" {
  description = "Labels applied to project"
  value       = local.labels
}
```

---

## Phase 3: Test Implementation

### Create First Client Project (Manual Test)

Create `clients/acme-corp/app1/terraform/main.tf`:
```hcl
terraform {
  backend "gcs" {
    bucket = "acme-corp-terraform-state"
    prefix = "app1/prod"
  }
}

provider "google" {
  region = "europe-north2"
}

# Create client folder
resource "google_folder" "client" {
  display_name = "acme-corp"
  parent       = "folders/${var.solvigo_folder_id}"
}

# Create production project
module "project" {
  source = "../../../../modules/gcp-project"

  client_name        = "acme-corp"
  project_name       = "app1"
  environment        = "prod"
  folder_id          = google_folder.client.name
  billing_account_id = var.billing_account_id
}
```

---

## Quick Start Checklist

- [ ] **Phase 1.1-1.3**: Set up GCP folder and platform projects
- [ ] **Phase 1.4**: Create Shared VPC Terraform config
- [ ] **Phase 1.5**: Deploy Shared VPC
- [ ] **Phase 2**: Build `gcp-project` module
- [ ] **Phase 3**: Test with one client project
- [ ] Continue with Load Balancer, DNS, Cloud Build modules
- [ ] Build Python CLI tool (automates all of the above)

---

## Next Documentation to Create

1. **Load Balancer Setup Guide** - Configure Global HTTPS LB with hierarchical routing
2. **DNS Configuration Guide** - Set up Cloud DNS with zone delegation
3. **Cloud Build Pipeline** - Central CI/CD for all client projects
4. **Python CLI Development Guide** - Automate project creation
5. **Migration Guide** - Import existing client infrastructure

---

**Ready to Start?** Begin with Phase 1 - you have all the architectural decisions locked in!

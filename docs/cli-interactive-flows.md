Yes# Solvigo CLI - Interactive Flow Design

**Design Philosophy:** Guide consultants through setup with minimal need to remember commands or flags.

---

## Interactive CLI Flow Examples

### Flow 1: Existing Project - Add Infrastructure

```bash
$ cd clients/acme-corp/app1/
$ solvigo

╔══════════════════════════════════════════════════════════════╗
║          🚀 Welcome to Solvigo CLI v1.0.0                    ║
╚══════════════════════════════════════════════════════════════╝

📂 Project detected: acme-corp/app1
   GCP Project: acme-corp-app1-prod
   Location: clients/acme-corp/app1/

What would you like to do?

  1. ✨ Add services to Terraform
  2. 🚀 Deploy infrastructure
  3. 📊 View project status
  4. 🔧 Configure settings
  5. 🆕 Create new project
  6. ❌ Exit

→ Enter choice (1-6): 1

────────────────────────────────────────────────────────────────

🔍 Scanning GCP project: acme-corp-app1-prod...

✓ Found Cloud Run services (2)
✓ Found Cloud SQL instances (1)
✓ Found Storage buckets (3)
✓ Found Secrets (5)
✓ Found Service Accounts (2)

────────────────────────────────────────────────────────────────

📦 Select services to add to Terraform:

Cloud Run Services:
  ☑ app1-frontend (europe-north1)
    Type: ○ Frontend  ○ Backend  ● Fullstack

  ☑ app1-api (europe-north1)
    Type: ○ Frontend  ● Backend  ○ Fullstack

Database:
  ☑ app1-db (Cloud SQL - PostgreSQL 15)
  ☐ app1-firestore (Firestore)

Storage:
  ☑ app1-uploads (europe-north2)
  ☐ app1-backups (europe-north2)
  ☐ terraform-state-12345 (auto-generated, skip)

Secrets:
  ☑ database-password
  ☑ stripe-api-key
  ☐ internal-api-token
  ☐ jwt-secret
  ☐ oauth-client-secret

Service Accounts:
  ☑ cloud-run-sa@acme-corp-app1-prod.iam.gserviceaccount.com
  ☐ terraform-sa@acme-corp-app1-prod.iam.gserviceaccount.com

APIs Enabled:
  ☑ Vertex AI (aiplatform.googleapis.com)
  ☐ BigQuery (bigquery.googleapis.com)
  ☐ Pub/Sub (pubsub.googleapis.com)

[Space] to select  [A] Select all  [N] None  [Enter] Continue

→ Selected: 8 items

────────────────────────────────────────────────────────────────

Load Balancer Configuration:

  Should these services be registered with the load balancer?

  app1-frontend:
    ☑ Register with LB
    Hostname: [app1.acme-corp.solvigo.ai]
    Enable CDN: ☑ Yes  ☐ No
    Enable IAP: ☐ Yes  ☑ No

  app1-api:
    ☑ Register with LB
    Hostname: [api.acme-corp.solvigo.ai]
    Enable CDN: ☐ Yes  ☑ No
    Enable IAP: ☐ Yes  ☑ No

[Enter] Continue

────────────────────────────────────────────────────────────────

📝 Generating Terraform configuration...

  ✓ Created main.tf
  ✓ Created cloud-run-frontend.tf
  ✓ Created cloud-run-backend.tf
  ✓ Created database.tf
  ✓ Created storage.tf
  ✓ Created secrets.tf
  ✓ Created service-accounts.tf
  ✓ Created load-balancer-backend.tf
  ✓ Created imports.tf (8 import blocks)

📁 Files created in: clients/acme-corp/app1/terraform/

────────────────────────────────────────────────────────────────

🔄 Next steps:

  1. Review generated Terraform:
     cd clients/acme-corp/app1/terraform
     cat main.tf

  2. Initialize Terraform:
     terraform init

  3. Import existing resources:
     terraform plan  # Should show 8 resources to import
     terraform apply

  4. Deploy any changes:
     solvigo deploy

Would you like to run these steps now? (y/n): y

────────────────────────────────────────────────────────────────

🚀 Running Terraform initialization...

$ terraform init

Initializing the backend...
✓ Backend configured successfully

Initializing modules...
✓ Downloaded cloud-run-app module
✓ Downloaded database module
✓ Downloaded storage module

Initializing providers...
✓ Installed google provider v5.45.0

Terraform has been successfully initialized!

────────────────────────────────────────────────────────────────

📋 Running Terraform plan...

$ terraform plan

Terraform will perform the following actions:

  # module.frontend.google_cloud_run_service.service will be imported
  # module.backend.google_cloud_run_service.service will be imported
  # module.database.google_sql_database_instance.instance will be imported
  # module.uploads.google_storage_bucket.bucket will be imported
  ... (4 more)

Plan: 0 to add, 0 to change, 0 to destroy, 8 to import.

────────────────────────────────────────────────────────────────

Apply these changes? (yes/no): yes

Importing resources...
✓ Imported module.frontend.google_cloud_run_service.service
✓ Imported module.backend.google_cloud_run_service.service
✓ Imported module.database.google_sql_database_instance.instance
✓ Imported module.uploads.google_storage_bucket.bucket
✓ Imported 8 resources successfully

────────────────────────────────────────────────────────────────

✅ Import complete!

Your existing infrastructure is now managed by Terraform.

Summary:
  - Cloud Run services: 2
  - Databases: 1
  - Storage buckets: 1
  - Secrets: 2
  - Service accounts: 1
  - Load balancer backends: 2

Next: Make changes in terraform/ and run 'solvigo deploy'
```

---

## Flow 2: Create New Project

```bash
$ cd ~/projects/
$ solvigo

╔══════════════════════════════════════════════════════════════╗
║          🚀 Welcome to Solvigo CLI v1.0.0                    ║
╚══════════════════════════════════════════════════════════════╝

What would you like to do?

  1. Create new project
  2. Choose existing project
  3. Import existing GCP project

→ Enter choice: 1

────────────────────────────────────────────────────────────────

🆕 Create New Project

Client name: techstart
  ✓ Client exists (folder: techstart/)
  ✓ DNS zone exists (techstart.solvigo.ai)
  ✓ State bucket exists (techstart-terraform-state)

Project name: dashboard

Environment:
  ○ Development only
  ○ Production only
  ● Both (recommended)
  ○ Dev, Staging, Production

Selected: dev, prod

────────────────────────────────────────────────────────────────

🏗️ Infrastructure Setup

What type of application is this?

  ● Fullstack (Frontend + Backend)
  ○ Frontend only
  ○ Backend only
  ○ API only
  ○ Custom

────────────────────────────────────────────────────────────────

Frontend Configuration:

  Framework:
    ● React + Vite
    ○ Next.js
    ○ Vue.js
    ○ Svelte
    ○ None (HTML/CSS/JS)

  TypeScript:
    ● Yes
    ○ No

  Features:
    ☑ Tailwind CSS
    ☐ React Router
    ☐ Redux/Zustand
    ☐ PWA support

────────────────────────────────────────────────────────────────

Backend Configuration:

  Framework:
    ● FastAPI
    ○ Django
    ○ Flask
    ○ Express.js
    ○ Go

  Python version:
    ○ 3.11
    ● 3.12 (recommended)
    ○ 3.13

  Features:
    ☑ JWT Authentication
    ☑ CORS middleware
    ☐ WebSocket support
    ☐ Background tasks (Celery)

────────────────────────────────────────────────────────────────

Database Configuration:

  Do you need a database?
    ● Yes
    ○ No

  Database type:
    ● Cloud SQL (PostgreSQL)
    ○ Cloud SQL (MySQL)
    ○ Firestore
    ○ Both SQL + Firestore

  PostgreSQL version:
    ○ 14
    ● 15 (recommended)
    ○ 16

  Instance size:
    ● db-f1-micro (Development, €7/month)
    ○ db-g1-small (Small production, €24/month)
    ○ db-n1-standard-1 (Production, €46/month)
    ○ Custom

  Backups:
    ● Automated daily backups
    ○ No backups (not recommended)

────────────────────────────────────────────────────────────────

Storage Configuration:

  Do you need storage buckets?
    ● Yes
    ○ No

  What for? (select multiple)
    ☑ User uploads
    ☑ Static assets
    ☐ Logs
    ☐ Backups
    ☐ ML models

────────────────────────────────────────────────────────────────

API Services:

  Which GCP APIs do you need?

  AI/ML:
    ☐ Vertex AI
    ☐ Translation API
    ☐ Vision API
    ☐ Natural Language API

  Data:
    ☐ BigQuery
    ☐ Pub/Sub
    ☐ Datastore

  Other:
    ☑ Secret Manager (auto-selected)
    ☑ Cloud Run (auto-selected)
    ☐ Cloud Tasks
    ☐ Cloud Scheduler

────────────────────────────────────────────────────────────────

Load Balancer Configuration:

  Domain:
    Primary: [dashboard.techstart.solvigo.ai]

  Additional domains (optional):
    [app.techstart.solvigo.ai]
    [+ Add another]

  CDN:
    ● Enable Cloud CDN
    ○ Disable

  Security:
    ☐ Enable Identity-Aware Proxy (IAP)
    ☑ Enable Cloud Armor (DDoS protection)

────────────────────────────────────────────────────────────────

📋 Project Summary

Client:       techstart
Project:      dashboard
Environments: dev, prod

Infrastructure:
  ✓ Frontend:     React + Vite + TypeScript + Tailwind
  ✓ Backend:      FastAPI (Python 3.12)
  ✓ Database:     PostgreSQL 15 (db-f1-micro)
  ✓ Storage:      2 buckets (uploads, static)
  ✓ Load Balancer: CDN enabled, Cloud Armor enabled
  ✓ Domains:      dashboard.techstart.solvigo.ai
                  app.techstart.solvigo.ai

Estimated monthly cost: €15-25

────────────────────────────────────────────────────────────────

Proceed with creation? (yes/no): yes

🚀 Creating project...

  ✓ Creating GCP projects
    - techstart-dashboard-dev
    - techstart-dashboard-prod

  ✓ Enabling APIs

  ✓ Creating directory structure
    clients/techstart/dashboard/
    ├── terraform/
    ├── app/
    │   ├── frontend/
    │   └── backend/
    └── cloudbuild.yaml

  ✓ Generating Terraform configuration

  ✓ Generating frontend code (React + Vite)

  ✓ Generating backend code (FastAPI)

  ✓ Creating Dockerfiles

  ✓ Creating Cloud Build config

────────────────────────────────────────────────────────────────

⚠️  Billing Account Required

The GCP projects have been created but need a billing account linked.

ACTION REQUIRED (by admin):
  gcloud billing projects link techstart-dashboard-dev \
    --billing-account=XXXXXX-XXXXXX-XXXXXX

  gcloud billing projects link techstart-dashboard-prod \
    --billing-account=XXXXXX-XXXXXX-XXXXXX

Notification sent to: kristi@solvigo.ai

Waiting for billing to be linked... (timeout in 5 minutes)
[Press Ctrl+C to skip and continue later]

────────────────────────────────────────────────────────────────

✓ Billing linked!

🚀 Deploying infrastructure...

  Deploying to dev environment:
  ✓ Terraform init
  ✓ Terraform plan
  ✓ Terraform apply
    - Created database instance
    - Created storage buckets
    - Registered with load balancer

  Deploying to prod environment:
  ✓ Terraform init
  ✓ Terraform plan
  ✓ Terraform apply
    - Created database instance
    - Created storage buckets
    - Registered with load balancer

────────────────────────────────────────────────────────────────

✅ Project created successfully!

📍 Location: clients/techstart/dashboard/

🌐 URLs (available in ~10 min after SSL provision):
  Dev:  https://dashboard.techstart.solvigo.ai
  Prod: https://dashboard.techstart.solvigo.ai (not deployed yet)

📝 Next steps:

  1. Navigate to project:
     cd clients/techstart/dashboard

  2. Review generated code:
     app/frontend/  - React application
     app/backend/   - FastAPI application

  3. Make changes and deploy:
     git add .
     git commit -m "Initial setup"
     git push

  4. Cloud Build will automatically deploy on push

💡 Useful commands:
  solvigo status           - View project status
  solvigo deploy           - Manual deployment
  solvigo logs             - View Cloud Run logs
  solvigo db:shell         - Connect to database

Happy coding! 🚀
```

---

## Flow 3: Import Existing GCP Project

```bash
$ solvigo

What would you like to do?

  1. Create new project
  2. Choose existing project
  3. Import existing GCP project

→ Enter choice: 3

────────────────────────────────────────────────────────────────

🔍 Import Existing GCP Project

GCP Project ID: legacy-app-12345

  ✓ Project found: legacy-app-12345
  ✓ You have owner permissions

────────────────────────────────────────────────────────────────

📦 Scanning project for resources...

  ✓ Found Cloud Run services (3)
  ✓ Found Cloud SQL instances (1)
  ✓ Found Firestore database
  ✓ Found Storage buckets (5)
  ✓ Found Secrets (12)
  ✓ Found Service Accounts (4)
  ✓ Found VPC connectors (1)
  ✓ Found 8 enabled APIs

────────────────────────────────────────────────────────────────

Organization:

  This project will be organized under:

  Client name: [acme-corp]
  Project name: [legacy-app]

  Directory: clients/acme-corp/legacy-app/

  This is a:
    ○ New client
    ● Existing client

────────────────────────────────────────────────────────────────

📦 Resource Selection

Select resources to import into Terraform:

Cloud Run Services:
  ☑ legacy-frontend (us-central1)
    → Type: ● Frontend  ○ Backend  ○ Fullstack
    → Register with LB: ● Yes  ○ No
    → Hostname: [legacy.acme-corp.solvigo.ai]

  ☑ legacy-backend (us-central1)
    → Type: ○ Frontend  ● Backend  ○ Fullstack
    → Register with LB: ● Yes  ○ No
    → Hostname: [api-legacy.acme-corp.solvigo.ai]

  ☐ old-worker (us-central1) [Deprecated service - skip?]

Databases:
  ☑ Cloud SQL: legacy-db (PostgreSQL 13)
  ☑ Firestore: (default database)

Storage Buckets:
  ☑ legacy-uploads-prod
  ☑ legacy-static-assets
  ☐ temp-bucket-2023 [Empty bucket - skip?]
  ☐ backup-20240115 [Old backup - skip?]
  ☐ logs-archived [Archive - skip?]

Secrets (12 found):
  ☑ Select all commonly used secrets
  ○ Select individually

    If Select individually:
    ☑ database-url
    ☑ redis-url
    ☑ stripe-secret-key
    ☑ sendgrid-api-key
    ☐ old-api-key-deprecated
    ☐ test-secret-do-not-use
    ... (6 more)

Service Accounts:
  ☑ cloud-run@legacy-app-12345.iam.gserviceaccount.com
  ☐ old-service-account@... [No recent activity - skip?]

────────────────────────────────────────────────────────────────

⚠️  Project Migration

Do you want to move this GCP project to the Solvigo organization?

Current location: Standalone project
Target location:  folders/212465532368/acme-corp/

Options:
  ● Keep in current location (safer, recommended)
  ○ Move to Solvigo folder (requires org admin)
  ○ Ask me later

Note: Project can be moved later if needed.

────────────────────────────────────────────────────────────────

📝 Generating Terraform configuration...

  Analyzing resource configurations...
  ✓ Detected Cloud Run settings
  ✓ Detected database configuration
  ✓ Detected IAM bindings
  ✓ Detected network settings

  Generating Terraform files...
  ✓ Created main.tf
  ✓ Created cloud-run.tf (2 services)
  ✓ Created database.tf
  ✓ Created storage.tf
  ✓ Created secrets.tf (8 secrets)
  ✓ Created service-accounts.tf
  ✓ Created imports.tf (15 import blocks)

  Creating backend configuration...
  ✓ Created backend.tf
  ✓ State bucket: acme-corp-terraform-state
  ✓ State prefix: legacy-app/prod

────────────────────────────────────────────────────────────────

✅ Import configuration generated!

📁 Location: clients/acme-corp/legacy-app/terraform/

📋 Summary:
  - Resources to import: 15
  - Cloud Run services: 2
  - Databases: 2 (SQL + Firestore)
  - Storage buckets: 2
  - Secrets: 8
  - Service accounts: 1

⚠️  Important: Review before applying!

Next steps:

  1. Review generated Terraform:
     cd clients/acme-corp/legacy-app/terraform
     less main.tf

  2. Initialize and import:
     terraform init
     terraform plan  # Verify 15 imports, 0 changes
     terraform apply

  3. Register with load balancer:
     solvigo deploy

Would you like to proceed with import now? (yes/no/review): review

────────────────────────────────────────────────────────────────

Opening editor...

[Editor opens with main.tf]

Press Enter when done reviewing...

────────────────────────────────────────────────────────────────

Proceed with import? (yes/no): yes

🚀 Running import...

$ cd clients/acme-corp/legacy-app/terraform
$ terraform init
$ terraform apply

Importing 15 resources...
✓ [1/15] Imported cloud-run-frontend
✓ [2/15] Imported cloud-run-backend
✓ [3/15] Imported database-instance
...
✓ [15/15] Imported service-account

────────────────────────────────────────────────────────────────

✅ Import complete!

Your existing GCP project is now managed by Terraform.

What's next?

  1. ✅ Infrastructure is now in Terraform state
  2. 🔄 Register with load balancer (optional):
     solvigo deploy --register-lb

  3. 📊 View project status:
     solvigo status

  4. 🎨 Add application code (if not already there):
     solvigo scaffold --frontend react --backend fastapi

All set! Your legacy project is now part of the Solvigo platform. 🎉
```

---

## CLI Technology Stack

### Recommended Libraries

**Core CLI Framework:**
- `click` - Command-line interface framework
- `rich` - Beautiful terminal formatting
- `questionary` - Interactive prompts

**Example:**
```python
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from questionary import select, checkbox, confirm, text

console = Console()

# Welcome screen
console.print(Panel.fit(
    "🚀 Welcome to Solvigo CLI v1.0.0",
    border_style="bold blue"
))

# Interactive selection
choice = select(
    "What would you like to do?",
    choices=[
        "✨ Add services to Terraform",
        "🚀 Deploy infrastructure",
        "📊 View project status",
        "🔧 Configure settings",
    ]
).ask()

# Checkbox selection
services = checkbox(
    "Select Cloud Run services:",
    choices=[
        {"name": "app1-frontend (europe-north1)", "checked": True},
        {"name": "app1-backend (europe-north1)", "checked": True},
    ]
).ask()

# Confirmation
if confirm("Proceed with import?").ask():
    with Progress() as progress:
        task = progress.add_task("Importing resources...", total=15)
        # ... import logic
```

### Directory Structure

```
cli/
├── setup.py
├── requirements.txt
├── solvigo/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   │
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── interactive.py   # Main interactive mode
│   │   ├── init.py          # Project creation
│   │   ├── import_cmd.py    # Import existing
│   │   ├── deploy.py        # Deployment
│   │   └── status.py        # Status viewing
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── prompts.py       # Reusable prompts
│   │   ├── display.py       # Rich console displays
│   │   └── validators.py    # Input validation
│   │
│   ├── gcp/
│   │   ├── __init__.py
│   │   ├── discovery.py     # Resource discovery
│   │   ├── projects.py      # Project management
│   │   └── apis.py          # API enablement
│   │
│   ├── terraform/
│   │   ├── __init__.py
│   │   ├── generator.py     # Terraform code generation
│   │   ├── runner.py        # Terraform execution
│   │   └── state.py         # State management
│   │
│   ├── templates/
│   │   ├── terraform/       # Jinja2 templates for TF
│   │   ├── react/           # React scaffolding
│   │   └── fastapi/         # FastAPI scaffolding
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config.py        # Configuration management
│       └── logging.py       # Logging setup
│
└── tests/
    ├── __init__.py
    ├── test_discovery.py
    └── test_terraform.py
```

---

## Implementation Notes

### Context Detection

```python
# solvigo/utils/context.py

def detect_project_context():
    """Detect if running from within a project directory."""
    cwd = Path.cwd()

    # Check if in clients/{client}/{project}/ structure
    if cwd.parts[-3] == 'clients':
        return {
            'client': cwd.parts[-2],
            'project': cwd.parts[-1],
            'path': cwd,
            'exists': True
        }

    # Check if terraform/ exists
    if (cwd / 'terraform').exists():
        # Try to infer from terraform backend config
        backend_config = parse_backend_config(cwd / 'terraform' / 'backend.tf')
        if backend_config:
            return {
                'client': backend_config['client'],
                'project': backend_config['project'],
                'path': cwd,
                'exists': True
            }

    return {'exists': False}
```

### Resource Type Detection

```python
# solvigo/gcp/discovery.py

def classify_cloud_run_service(service_name, service_config):
    """Automatically classify Cloud Run service as frontend/backend."""

    # Check environment variables
    env_vars = service_config.get('template', {}).get('spec', {}).get('containers', [{}])[0].get('env', [])

    # Frontend indicators
    frontend_indicators = ['REACT_APP', 'VITE_', 'NEXT_PUBLIC_', 'NODE_ENV']
    # Backend indicators
    backend_indicators = ['DATABASE_URL', 'REDIS_URL', 'SQLALCHEMY', 'DJANGO_SETTINGS']

    frontend_score = sum(1 for env in env_vars if any(ind in env['name'] for ind in frontend_indicators))
    backend_score = sum(1 for env in env_vars if any(ind in env['name'] for ind in backend_indicators))

    if frontend_score > backend_score:
        return 'frontend'
    elif backend_score > frontend_score:
        return 'backend'
    else:
        return 'unknown'  # Ask user
```

---

This interactive design makes the CLI much more user-friendly and reduces the need to remember complex command syntax!

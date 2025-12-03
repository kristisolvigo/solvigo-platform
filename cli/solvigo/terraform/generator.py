"""
Terraform code generator - creates Terraform configurations from selected resources
"""
from pathlib import Path
from typing import Dict, List
from jinja2 import Template
from rich.console import Console
import shutil

from solvigo.utils.bootstrap import PLATFORM_PROJECT_NUMBER

console = Console()


def sanitize_terraform_name(name: str, resource_type: str = 'resource') -> str:
    """
    Sanitize name to be a valid Terraform identifier.

    Terraform identifiers must:
    - Start with a letter or underscore
    - Contain only letters, digits, underscores, and hyphens

    Args:
        name: Raw name (e.g., "1064116177689-compute@...", "my-bucket-123")
        resource_type: Type hint for prefixing ('service_account', 'bucket', 'database', etc.)

    Returns:
        Valid Terraform identifier

    Examples:
        sanitize_terraform_name("1064-compute@project.iam", "service_account")
        → "sa_1064_compute"

        sanitize_terraform_name("123-my-bucket", "bucket")
        → "bucket_123_my_bucket"
    """
    # Remove domain suffixes and special characters
    name = name.split('@')[0]  # Remove @domain.com
    name = name.replace('.gserviceaccount.com', '')
    name = name.replace('.iam', '')
    name = name.replace('-', '_')
    name = name.replace('.', '_')

    # Remove any other invalid characters
    name = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)

    # If starts with digit, prepend appropriate prefix
    if name and name[0].isdigit():
        prefix_map = {
            'service_account': 'sa_',
            'bucket': 'bucket_',
            'database': 'db_',
            'cloud_run': 'service_',
            'secret': 'secret_',
        }
        prefix = prefix_map.get(resource_type, 'res_')
        name = f"{prefix}{name}"

    # Ensure result is not empty and starts with letter/underscore
    if not name or not (name[0].isalpha() or name[0] == '_'):
        name = f"{resource_type}_{name}" if name else resource_type

    return name


def sanitize_label_value(value: str) -> str:
    """
    Sanitize value to be a valid GCP label value.

    GCP label values must:
    - Only contain lowercase letters, numeric characters, underscores and dashes
    - Be at most 63 characters long
    - Can be empty

    Args:
        value: Raw label value (e.g., "My Project Name", "Galleriet Seo")

    Returns:
        Valid GCP label value

    Examples:
        sanitize_label_value("My Project Name") → "my-project-name"
        sanitize_label_value("Galleriet Seo") → "galleriet-seo"
        sanitize_label_value("Test_123") → "test_123"
    """
    # Convert to lowercase
    value = value.lower()

    # Replace spaces with hyphens
    value = value.replace(' ', '-')

    # Remove any characters that aren't lowercase letters, numbers, underscores, or hyphens
    value = ''.join(c if c.islower() or c.isdigit() or c in ('_', '-') else '' for c in value)

    # Remove consecutive hyphens/underscores
    import re
    value = re.sub(r'[-_]+', lambda m: m.group(0)[0], value)

    # Trim to 63 characters
    value = value[:63]

    # Remove leading/trailing hyphens or underscores
    value = value.strip('-_')

    return value


def append_to_tf_file(file_path: Path, content: str, resource_id: str) -> bool:
    """
    Append content to Terraform file if resource doesn't already exist.

    Args:
        file_path: Path to terraform file
        content: Content to append
        resource_id: Unique identifier to check for duplicates

    Returns:
        True if appended, False if already exists
    """
    if not file_path.exists():
        file_path.write_text(content)
        return True

    existing = file_path.read_text()

    # Check if resource already exists
    if resource_id in existing:
        return False

    # Append
    with open(file_path, 'a') as f:
        f.write("\n\n")
        f.write(content)

    return True


def copy_terraform_modules(output_dir: Path):
    """
    Copy bundled Terraform modules to client repository.

    Copies from CLI's terraform_templates/ to client repo's terraform/modules/
    """
    # Get CLI's terraform_templates directory
    cli_templates_dir = Path(__file__).parent.parent / 'terraform_templates'

    if not cli_templates_dir.exists():
        console.print(f"[yellow]⚠ Terraform templates not found at {cli_templates_dir}[/yellow]")
        return False

    # Copy to client repo
    modules_dir = output_dir / 'modules'

    if modules_dir.exists():
        console.print(f"  [dim]Terraform modules already exist at {modules_dir}[/dim]")
        return True

    try:
        console.print(f"  [cyan]Copying Terraform modules...[/cyan]")
        shutil.copytree(cli_templates_dir, modules_dir)
        console.print(f"  [green]✓ Modules copied to terraform/modules/[/green]")
        return True
    except Exception as e:
        console.print(f"  [yellow]⚠ Could not copy modules: {e}[/yellow]")
        return False


def generate_terraform_config(
    client: str,
    project: str,
    selected_resources: Dict[str, List],
    output_dir: Path,
    gcp_project_id: str,
    client_subdomain: str = None,
    project_subdomain: str = None
) -> bool:
    """
    Generate Terraform configuration from selected resources.

    Args:
        client: Client name
        project: Project name
        selected_resources: Dict of selected resources
        output_dir: Output directory for Terraform files
        gcp_project_id: GCP project ID from database
        client_subdomain: Client subdomain from database (for SA naming)
        project_subdomain: Project subdomain from database (for SA naming)

    Returns:
        True if successful, False otherwise
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[cyan]📝 Generating Terraform configuration...[/cyan]\n")

    # Copy bundled Terraform modules to client repo
    copy_terraform_modules(output_dir)

    try:
        # Generate backend.tf
        generate_backend_tf(client, project, output_dir)
        console.print("  ✓ Created backend.tf")

        # Generate variables.tf
        generate_variables_tf(client, project, gcp_project_id, output_dir)
        console.print("  ✓ Created variables.tf")

        # Generate main.tf with provider
        generate_main_tf(client, project, output_dir)
        console.print("  ✓ Created main.tf")

        # Generate deployer service account
        generate_deployer_sa_tf(output_dir)
        console.print("  ✓ Created deployer-sa.tf")

        # Generate APIs enablement
        generate_apis_tf(selected_resources, output_dir)
        console.print("  ✓ Created apis.tf")

        # IMPORTANT: Generate service accounts FIRST (before Cloud Run)
        # This ensures service account emails exist before modules reference them
        has_database = bool(selected_resources.get('cloud_sql') or selected_resources.get('firestore'))
        cloud_run_services = selected_resources.get('cloud_run', [])
        existing_sas = selected_resources.get('service_accounts', [])
        enable_vertex_ai = bool(selected_resources.get('apis') and 'aiplatform.googleapis.com' in selected_resources.get('apis', []))

        generate_service_accounts_tf(
            client, project, existing_sas, output_dir,
            cloud_run_services=cloud_run_services,
            has_database=has_database,
            enable_vertex_ai=enable_vertex_ai,
            client_subdomain=client_subdomain,
            project_subdomain=project_subdomain
        )
        console.print("  ✓ Created service-accounts.tf")

        # Generate Cloud Run resources (now SAs exist)
        if cloud_run_services:
            generate_cloud_run_tf(
                client, project, cloud_run_services, output_dir,
                has_database=has_database
            )
            console.print("  ✓ Created cloud-run.tf")

        # Generate database resources
        if selected_resources.get('cloud_sql'):
            generate_cloud_sql_tf(client, project, selected_resources['cloud_sql'], output_dir)
            console.print("  ✓ Created database-sql.tf")

            # NEW: Generate migration job if database exists
            db_instance_name = selected_resources['cloud_sql'][0]['name']
            generate_migration_job_tf(client, project, db_instance_name, output_dir)
            console.print("  ✓ Created migration-job.tf")

        if selected_resources.get('firestore'):
            generate_firestore_tf(client, project, selected_resources['firestore'], output_dir)
            console.print("  ✓ Created database-firestore.tf")

        # Generate storage resources
        if selected_resources.get('storage'):
            generate_storage_tf(client, project, selected_resources['storage'], output_dir)
            console.print("  ✓ Created storage.tf")

        # Generate secrets resources
        if selected_resources.get('secrets'):
            generate_secrets_tf(client, project, selected_resources['secrets'], output_dir)
            console.print("  ✓ Created secrets.tf")

        # Generate VPC data sources if there's a database and Cloud Run services
        if has_database and cloud_run_services:
            generate_vpc_tf(client, project, output_dir)
            console.print("  ✓ Created vpc.tf")
            generate_vpc_connector_tf(client, project, output_dir)
            console.print("  ✓ Created vpc-connector.tf")

        # Generate import blocks
        generate_imports_tf(client, project, selected_resources, output_dir, gcp_project_id)
        console.print("  ✓ Created imports.tf")

        # Generate outputs.tf
        generate_outputs_tf(client, project, selected_resources, output_dir)
        console.print("  ✓ Created outputs.tf")

        console.print(f"\n[green]✓ Terraform configuration generated in:[/green] {output_dir}\n")
        return True

    except Exception as e:
        console.print(f"\n[red]✗ Error generating Terraform: {e}[/red]\n")
        return False


def generate_backend_tf(client: str, project: str, output_dir: Path):
    """Generate backend.tf for remote state"""
    # Normalize to lowercase for GCS bucket name (required)
    client_slug = client.lower().replace(' ', '-')
    project_slug = project.lower().replace(' ', '-')

    template = Template("""terraform {
  backend "gcs" {
    bucket = "{{ client_slug }}-terraform-state"
    prefix = "{{ project_slug }}/prod"
  }

  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}
""")

    content = template.render(client_slug=client_slug, project_slug=project_slug)
    (output_dir / 'backend.tf').write_text(content)


def generate_deployer_sa_tf(output_dir: Path):
    """
    Generate Terraform for deployer service account.

    Note: This SA is created via CLI bootstrap (gcloud commands) before terraform runs.
    Terraform will import and manage it going forward.
    """
    template = Template("""# Deployer Service Account
# Created via CLI bootstrap, managed by Terraform going forward
resource "google_service_account" "deployer" {
  account_id   = "deployer"
  display_name = "Cloud Build Deployer"
  description  = "Service account for deploying services via Cloud Build"
  project      = var.project_id
}

# Grant permissions to deployer SA
resource "google_project_iam_member" "deployer_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

# Allow Cloud Build to impersonate deployer SA
resource "google_service_account_iam_member" "deployer_user" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:{{ platform_project_number }}@cloudbuild.gserviceaccount.com"
}

# Output deployer SA email for reference
output "deployer_sa_email" {
  value       = google_service_account.deployer.email
  description = "Deployer service account email"
}
""")

    content = template.render(platform_project_number=PLATFORM_PROJECT_NUMBER)
    (output_dir / 'deployer-sa.tf').write_text(content)


def generate_variables_tf(client: str, project: str, gcp_project_id: str, output_dir: Path):
    """Generate variables.tf with actual GCP project ID from database"""
    # Sanitize label values to comply with GCP requirements
    client_label = sanitize_label_value(client)
    project_label = sanitize_label_value(project)

    template = Template("""variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "{{ project_id }}"
}

variable "region" {
  description = "Default GCP region"
  type        = string
  default     = "europe-north2"
}

variable "client_name" {
  description = "Client name"
  type        = string
  default     = "{{ client }}"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "{{ project }}"
}

variable "environment" {
  description = "Environment"
  type        = string
  default     = "prod"
}

variable "labels" {
  description = "Standard labels"
  type        = map(string)
  default = {
    client      = "{{ client_label }}"
    project     = "{{ project_label }}"
    environment = "prod"
    managed_by  = "terraform"
    cost_center = "client-billable"
  }
}

variable "shared_vpc_project" {
  description = "Shared VPC host project ID"
  type        = string
  default     = "solvigo-platform-prod"
}

variable "shared_vpc_name" {
  description = "Shared VPC network name"
  type        = string
  default     = "solvigo-shared-vpc"
}
""")

    # Use actual GCP project ID from database
    content = template.render(
        client=client,
        project=project,
        project_id=gcp_project_id,
        client_label=client_label,
        project_label=project_label
    )
    (output_dir / 'variables.tf').write_text(content)


def generate_main_tf(client: str, project: str, output_dir: Path):
    """Generate main.tf with provider configuration"""
    template = Template("""# {{ client }} / {{ project }}
# Generated by Solvigo CLI

provider "google" {
  project = var.project_id
  region  = var.region
}

# Local variables
locals {
  labels = var.labels
}
""")

    content = template.render(client=client, project=project)
    (output_dir / 'main.tf').write_text(content)


def generate_apis_tf(
    selected_resources: Dict[str, List],
    output_dir: Path
):
    """Generate APIs enablement configuration"""

    # Base APIs always enabled
    apis = [
        "run.googleapis.com",
        "sqladmin.googleapis.com",
        "compute.googleapis.com",
        "servicenetworking.googleapis.com",
        "vpcaccess.googleapis.com",
        "cloudresourcemanager.googleapis.com",
    ]

    # Add Vertex AI if requested
    if 'apis' in selected_resources and selected_resources['apis']:
        apis.extend(selected_resources['apis'])

    template = Template("""# Enable required GCP APIs

resource "google_project_service" "required_apis" {
  for_each = toset([
{% for api in apis %}
    "{{ api }}",
{% endfor %}
  ])

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}
""")

    content = template.render(apis=apis)
    (output_dir / 'apis.tf').write_text(content)


def generate_cloud_run_tf(client: str, project: str, services: List[Dict], output_dir: Path, append: bool = False, has_database: bool = False):
    """
    Generate Cloud Run service configurations.

    Args:
        append: If True, append to existing file instead of overwriting
        has_database: Whether project has a database (enables VPC connector)
    """
    import re

    # Sanitize project name for resource naming
    project_slug = project.lower().replace(' ', '-').replace('_', '-')
    project_slug = re.sub(r'[^a-z0-9-]', '', project_slug)
    project_slug = re.sub(r'-+', '-', project_slug).strip('-')

    file_path = output_dir / 'cloud-run.tf'

    if append and file_path.exists():
        # Append mode - add new services without overwriting
        existing_content = file_path.read_text()

        for service in services:
            service_name = service['name']
            module_name = service_name.replace('-', '_')

            # Check if module already exists
            if f'module "{module_name}"' in existing_content:
                console.print(f"  [dim]{service_name} already exists (skipping)[/dim]")
                continue

            # Generate and append
            if service.get('_create'):
                module_code = generate_cloud_run_module(client, project, service, project_slug, has_database)
            else:
                module_code = generate_cloud_run_import_module(client, project, service, project_slug, has_database)

            with open(file_path, 'a') as f:
                f.write("\n\n")
                f.write(module_code)
    else:
        # Normal mode - generate full file
        lines = ["# Cloud Run Services\n"]

        for service in services:
            if service.get('_create'):
                # New service - use module
                lines.append(generate_cloud_run_module(client, project, service, project_slug, has_database))
            else:
                # Existing service - use module with import
                lines.append(generate_cloud_run_import_module(client, project, service, project_slug, has_database))

        file_path.write_text('\n'.join(lines))


def generate_cloud_run_module(client: str, project: str, service: Dict, project_slug: str, has_database: bool = False) -> str:
    """Generate module configuration for Cloud Run service"""
    service_name = service['name']
    service_type = service.get('type', 'backend')
    region = service.get('region', 'europe-north2')

    # Construct service account resource name
    sa_name = f"{project_slug}-{service_type}-app"
    sa_resource_name = sa_name.replace('-', '_')

    # VPC connector config
    vpc_connector_config = ""
    if has_database:
        vpc_connector_config = """
  # Connect to VPC for Cloud SQL access
  vpc_connector_name = data.google_vpc_access_connector.cloud_run_connector.id
"""

    # Service account config (use local value to avoid count dependency issues)
    sa_config = f"""
  # Use custom service account
  service_account_email = local.{sa_resource_name}_email
"""

    template = Template("""
# {{ service_name }} ({{ service_type }})
# Note: Initial deployment uses placeholder image (gcr.io/cloudrun/hello)
# Your CI/CD pipeline will deploy the real application image
# Terraform manages infrastructure; CI/CD manages deployments
module "{{ module_name }}" {
  source = "./modules/cloud-run-app"

  project_id   = var.project_id
  service_name = "{{ service_name }}"
  region       = "{{ region }}"

  # image defaults to gcr.io/cloudrun/hello for initial deployment
  # CI/CD will update to real image via Cloud Build
  # See modules/cloud-run-app/README.md for details
{{ sa_config }}{{ vpc_connector_config }}
  labels = local.labels
}
""")

    module_name = service_name.replace('-', '_')

    return template.render(
        service_name=service_name,
        service_type=service_type,
        module_name=module_name,
        region=region,
        sa_config=sa_config,
        vpc_connector_config=vpc_connector_config
    )


def generate_cloud_run_import_module(client: str, project: str, service: Dict, project_slug: str, has_database: bool = False) -> str:
    """Generate module configuration for existing Cloud Run service with import"""
    # For now, same as new service
    # Import block will be in imports.tf
    return generate_cloud_run_module(client, project, service, project_slug, has_database)


def generate_cloud_sql_tf(client: str, project: str, instances: List[Dict], output_dir: Path, append: bool = False):
    """Generate Cloud SQL configurations"""
    lines = ["# Cloud SQL Databases\n"]

    for db in instances:
        if db.get('_create'):
            lines.append(generate_cloud_sql_module(client, project, db))
        else:
            lines.append(generate_cloud_sql_import_module(client, project, db))

    (output_dir / 'database-sql.tf').write_text('\n'.join(lines))


def generate_cloud_sql_module(client: str, project: str, db: Dict) -> str:
    """Generate module configuration for Cloud SQL"""
    import re

    db_name = db['name']
    db_version = db.get('database_version', 'POSTGRES_15')
    tier = db.get('tier', 'db-g1-small')

    # Construct backend service account resource name
    project_slug = project.lower().replace(' ', '-').replace('_', '-')
    project_slug = re.sub(r'[^a-z0-9-]', '', project_slug)
    project_slug = re.sub(r'-+', '-', project_slug).strip('-')
    backend_sa_name = f"{project_slug}-backend-app"
    backend_sa_resource = backend_sa_name.replace('-', '_')

    template = Template("""
# Cloud SQL: {{ db_name }}
module "{{ module_name }}" {
  source = "./modules/database-cloudsql"

  project_id       = var.project_id
  instance_name    = "{{ db_name }}"
  database_version = "{{ db_version }}"
  tier             = "{{ tier }}"
  region           = var.region

  enable_backups = {{ enable_backups }}

  # Network configuration - use Shared VPC for private connectivity
  private_network = data.google_compute_network.shared_vpc.id
  public_ip       = false

  # IAM user for application service account
  app_service_account_email = local.{{ backend_sa_resource }}_email

  labels = local.labels

  depends_on = [
    google_project_service.required_apis["sqladmin.googleapis.com"],
    google_project_service.required_apis["servicenetworking.googleapis.com"]
  ]
}
""")

    module_name = db_name.replace('-', '_')
    enable_backups = str(db.get('backups', True)).lower()

    return template.render(
        db_name=db_name,
        module_name=module_name,
        db_version=db_version,
        tier=tier,
        enable_backups=enable_backups,
        backend_sa_resource=backend_sa_resource
    )


def generate_cloud_sql_import_module(client: str, project: str, db: Dict) -> str:
    """Generate module for existing Cloud SQL with import"""
    return generate_cloud_sql_module(client, project, db)


def generate_migration_job_tf(
    client: str,
    project: str,
    database_instance_name: str,
    output_dir: Path
):
    """Generate Cloud Run migration job configuration"""
    import re

    project_slug = project.lower().replace(' ', '-').replace('_', '-')
    project_slug = re.sub(r'[^a-z0-9-]', '', project_slug)

    job_name = f"{project_slug}-db-migrations"

    template = Template("""# Database Migration Job

module "db_migrations" {
  source = "./modules/cloud-run-migration-job"

  project_id                = var.project_id
  job_name                  = "{{ job_name }}"
  region                    = var.region
  service_account_email     = local.{{ backend_sa_resource }}_email
  deployer_sa_email         = google_service_account.deployer.email
  cloud_sql_connection_name = module.{{ db_module_name }}.connection_name
  vpc_connector_name        = data.google_vpc_access_connector.cloud_run_connector.id

  env_vars = {
    MIGRATION_TOOL = "alembic"  # Adjust based on your migration tool
  }

  labels = local.labels

  depends_on = [
    google_project_service.required_apis["run.googleapis.com"],
    module.{{ db_module_name }},
    google_service_account.{{ backend_sa_resource }}
  ]
}
""")

    # Construct backend SA resource name
    backend_sa_name = f"{project_slug}-backend-app"
    backend_sa_resource = backend_sa_name.replace('-', '_')

    # Database module name
    db_module_name = database_instance_name.replace('-', '_')

    content = template.render(
        job_name=job_name,
        backend_sa_resource=backend_sa_resource,
        db_module_name=db_module_name
    )

    (output_dir / 'migration-job.tf').write_text(content)


def generate_firestore_tf(client: str, project: str, databases: List[Dict], output_dir: Path):
    """Generate Firestore configurations"""
    lines = ["# Firestore Database\n"]

    for db in databases:
        if db.get('_create'):
            lines.append(generate_firestore_module(client, project, db))
        # Existing Firestore can't really be imported easily, it just exists

    (output_dir / 'database-firestore.tf').write_text('\n'.join(lines))


def generate_firestore_module(client: str, project: str, db: Dict) -> str:
    """Generate Firestore database configuration"""
    template = Template("""
# Firestore Database
module "firestore" {
  source = "./modules/database-firestore"

  project_id = var.project_id
  location   = "{{ location }}"
  mode       = "{{ mode }}"

  labels = local.labels

  depends_on = [
    google_project_service.required_apis["firestore.googleapis.com"]
  ]
}
""")

    return template.render(
        location=db.get('location', 'eur3'),
        mode=db.get('mode', 'FIRESTORE_NATIVE')
    )


def generate_storage_tf(client: str, project: str, buckets: List[Dict], output_dir: Path, append: bool = False):
    """Generate storage bucket configurations"""
    lines = ["# Storage Buckets\n"]

    for bucket in buckets:
        if bucket.get('_create'):
            lines.append(generate_storage_module(client, project, bucket))
        else:
            lines.append(generate_storage_import_module(client, project, bucket))

    (output_dir / 'storage.tf').write_text('\n'.join(lines))


def generate_storage_module(client: str, project: str, bucket: Dict) -> str:
    """Generate storage bucket module"""
    bucket_name = bucket['name']
    location = bucket.get('location', 'europe-north2')

    # Sanitize module name (handles names starting with numbers)
    module_name = sanitize_terraform_name(bucket_name, 'bucket')

    template = Template("""
# Storage: {{ bucket_name }}
module "{{ module_name }}" {
  source = "./modules/storage-bucket"

  project_id  = var.project_id
  bucket_name = "{{ bucket_name }}"
  location    = "{{ location }}"

  labels = local.labels
}
""")

    return template.render(
        bucket_name=bucket_name,
        module_name=module_name,
        location=location
    )


def generate_storage_import_module(client: str, project: str, bucket: Dict) -> str:
    """Generate storage bucket for import"""
    return generate_storage_module(client, project, bucket)


def generate_secrets_tf(client: str, project: str, secrets: List[Dict], output_dir: Path, append: bool = False):
    """Generate Secret Manager configurations"""
    lines = ["# Secrets\n"]

    for secret in secrets:
        secret_name = secret['name']
        resource_name = secret_name.replace('-', '_')

        lines.append(f"""
# Secret: {secret_name}
resource "google_secret_manager_secret" "{resource_name}" {{
  secret_id = "{secret_name}"
  project   = var.project_id

  replication {{
    auto {{}}
  }}

  labels = local.labels
}}
""")

    (output_dir / 'secrets.tf').write_text('\n'.join(lines))


def generate_service_accounts_tf(
    client: str,
    project: str,
    accounts: List[Dict],
    output_dir: Path,
    append: bool = False,
    cloud_run_services: List[Dict] = None,
    has_database: bool = False,
    enable_vertex_ai: bool = False,
    client_subdomain: str = None,
    project_subdomain: str = None
):
    """
    Generate service account configurations.

    Args:
        client: Client name
        project: Project name
        accounts: Existing service accounts to import
        output_dir: Output directory
        append: Whether to append to existing file
        cloud_run_services: List of Cloud Run services (to create SAs for)
        has_database: Whether project has a database (grants cloudsql.client role)
        client_subdomain: Client subdomain from database (for SA naming)
        project_subdomain: Project subdomain from database (for SA naming)
    """
    import re

    lines = ["# Service Accounts\n"]

    # Use subdomains for SA naming (shorter, cleaner names)
    # Fallback to slugified names if subdomains not provided (backward compatibility)
    if client_subdomain and project_subdomain:
        # Use subdomains directly from database
        sa_prefix = f"{client_subdomain}-{project_subdomain}"
    else:
        # Fallback: derive from client/project names
        client_slug = client.lower().replace(' ', '-').replace('_', '-')
        client_slug = re.sub(r'[^a-z0-9-]', '', client_slug)
        client_slug = re.sub(r'-+', '-', client_slug).strip('-')

        project_slug = project.lower().replace(' ', '-').replace('_', '-')
        project_slug = re.sub(r'[^a-z0-9-]', '', project_slug)
        project_slug = re.sub(r'-+', '-', project_slug).strip('-')

        sa_prefix = f"{project_slug}"

    # Deployer SA is in the client's project, not in solvigo-platform-prod
    deployer_sa_email = "google_service_account.deployer.email"

    # Build locals for service account emails (determinable at plan time)
    sa_email_locals = []
    if cloud_run_services:
        for service in cloud_run_services:
            service_type = service.get('type', 'backend')
            sa_name = f"{sa_prefix}-{service_type}-app"
            resource_name = sa_name.replace('-', '_')
            # Full service account email format
            sa_email_locals.append(f'  {resource_name}_email = "{sa_name}@${{var.project_id}}.iam.gserviceaccount.com"')

    sa_emails_block = "\n".join(sa_email_locals)

    lines.append(f"""
# Data source for project number (used to construct Compute Engine SA email)
data "google_project" "project" {{
  project_id = var.project_id
}}

# Service account emails (computed from known values at plan time)
locals {{
  compute_sa_email = "${{data.google_project.project.number}}-compute@developer.gserviceaccount.com"
{sa_emails_block}
}}

""")

    lines.append(f"""# Deployer Service Account Permissions
# Grant deployer SA Cloud Run Admin role
resource "google_project_iam_member" "deployer_cloudrun_admin" {{
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${{{deployer_sa_email}}}"
}}

# Grant deployer SA permission to act as Compute Engine SA (required for Cloud Run deployments)
resource "google_service_account_iam_member" "deployer_compute_sa_user" {{
  service_account_id = "projects/${{var.project_id}}/serviceAccounts/${{local.compute_sa_email}}"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${{{deployer_sa_email}}}"
}}
""")

    # Generate service accounts for Cloud Run services
    if cloud_run_services:
        for service in cloud_run_services:
            service_name = service['name']
            service_type = service.get('type', 'backend')
            sa_name = f"{sa_prefix}-{service_type}-app"
            resource_name = sa_name.replace('-', '_')

            lines.append(f"""
# Service Account for Cloud Run {service_type}
resource "google_service_account" "{resource_name}" {{
  account_id   = "{sa_name}"
  display_name = "{project} {service_type.capitalize()} Application"
  project      = var.project_id
}}

# Grant deployer permission to act as {service_type} SA
resource "google_service_account_iam_member" "deployer_{resource_name}_user" {{
  service_account_id = google_service_account.{resource_name}.id
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${{{deployer_sa_email}}}"
}}
""")

            # Grant Cloud SQL Client role if there's a database
            if has_database:
                lines.append(f"""
# Grant Cloud SQL Client role to {service_type}
resource "google_project_iam_member" "{resource_name}_cloudsql_client" {{
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${{google_service_account.{resource_name}.email}}"
}}

# Grant Cloud SQL Instance User role for IAM authentication
resource "google_project_iam_member" "{resource_name}_cloudsql_instance_user" {{
  project = var.project_id
  role    = "roles/cloudsql.instanceUser"
  member  = "serviceAccount:${{google_service_account.{resource_name}.email}}"
}}
""")

            # Grant Vertex AI permissions if enabled (backend only)
            if enable_vertex_ai and service_type == 'backend':
                lines.append(f"""
# Grant Vertex AI User role to {service_type}
resource "google_project_iam_member" "{resource_name}_vertexai_user" {{
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${{google_service_account.{resource_name}.email}}"
}}
""")

            # Add output for service account email
            lines.append(f"""
output "{resource_name}_sa_email" {{
  description = "Email of the {service_type} service account"
  value       = google_service_account.{resource_name}.email
}}
""")

    for sa in accounts:
        email = sa['email']
        original_account_id = email.split('@')[0]
        display_name = sa.get('display_name', original_account_id)

        # Sanitize both resource name AND account_id (GCP requires account_id to start with letter)
        resource_name = sanitize_terraform_name(email, 'service_account')
        # For account_id, if starts with number, skip importing this SA (it's a Google-managed one)
        if original_account_id[0].isdigit():
            console.print(f"  [dim]Skipping Google-managed SA: {original_account_id} (starts with number)[/dim]")
            continue

        lines.append(f"""
# Service Account: {original_account_id}
resource "google_service_account" "{resource_name}" {{
  account_id   = "{original_account_id}"
  display_name = "{display_name}"
  project      = var.project_id
}}
""")

    (output_dir / 'service-accounts.tf').write_text('\n'.join(lines))


def generate_vpc_tf(client: str, project: str, output_dir: Path):
    """
    Generate VPC data source reference.

    References the shared VPC from the host project that this service project
    is attached to.
    """
    template = Template("""# Shared VPC Configuration
# This project is attached as a service project to the platform's shared VPC

# Data source to reference shared VPC from host project
data "google_compute_network" "shared_vpc" {
  name    = var.shared_vpc_name
  project = var.shared_vpc_project
}
""")

    content = template.render()
    (output_dir / 'vpc.tf').write_text(content)


def generate_vpc_connector_tf(client: str, project: str, output_dir: Path):
    """
    Generate VPC connector data source reference.

    References the existing serverless VPC connector in the shared VPC host project
    to allow Cloud Run services to connect to Cloud SQL instances via private IP.

    NOTE: The VPC connector must already exist in the host project.
    Uses the shared regional connector (e.g., solvigo-vpc-connector-north2).
    """
    # Use the shared VPC connector per region
    # Format: solvigo-vpc-connector-{region_suffix}
    # europe-north2 -> north2, europe-north1 -> north1
    template = Template("""# VPC Access Connector for Cloud Run to Cloud SQL
# Required for Cloud Run to connect to Cloud SQL private IP
#
# NOTE: For Shared VPC, the VPC connector is created in the HOST project
# (solvigo-platform-prod) and shared with all service projects.
# We reference the existing shared connector here rather than creating it.

data "google_vpc_access_connector" "cloud_run_connector" {
  name    = "solvigo-connector-n2"
  project = var.shared_vpc_project
  region  = "europe-north2"
}

output "vpc_connector_name" {
  description = "VPC connector full name for Cloud Run"
  value       = data.google_vpc_access_connector.cloud_run_connector.id
}
""")

    content = template.render(
    )

    (output_dir / 'vpc-connector.tf').write_text(content)


def generate_imports_tf(client: str, project: str, selected_resources: Dict[str, List], output_dir: Path, gcp_project_id: str, append: bool = False):
    """Generate import blocks for existing resources using actual GCP project ID"""
    lines = ["# Terraform Import Blocks\n"]
    lines.append("# These import blocks will bring existing GCP resources into Terraform state\n\n")

    # Use actual GCP project ID from database
    project_id = gcp_project_id

    # Import deployer service account (if it exists, Terraform will import it gracefully)
    lines.append(f"""# Deployer Service Account (created via CLI bootstrap)
import {{
  to = google_service_account.deployer
  id = "projects/{project_id}/serviceAccounts/deployer@{project_id}.iam.gserviceaccount.com"
}}

""")

    # Cloud Run imports
    for service in selected_resources.get('cloud_run', []):
        if not service.get('_create'):  # Only import existing
            service_name = service['name']
            region = service.get('region', 'europe-north2')
            module_name = service_name.replace('-', '_')

            lines.append(f"""import {{
  to = module.{module_name}.google_cloud_run_service.service
  id = "locations/{region}/namespaces/{project_id}/services/{service_name}"
}}
""")

    # Storage imports
    for bucket in selected_resources.get('storage', []):
        if not bucket.get('_create'):  # Only import existing
            bucket_name = bucket['name']

            # Sanitize module name (handles names starting with numbers)
            module_name = sanitize_terraform_name(bucket_name, 'bucket')

            lines.append(f"""import {{
  to = module.{module_name}.google_storage_bucket.bucket
  id = "{bucket_name}"
}}
""")

    # Secret imports
    for secret in selected_resources.get('secrets', []):
        secret_name = secret['name']
        resource_name = secret_name.replace('-', '_')

        lines.append(f"""import {{
  to = google_secret_manager_secret.{resource_name}
  id = "projects/{project_id}/secrets/{secret_name}"
}}
""")

    # Service account imports
    for sa in selected_resources.get('service_accounts', []):
        email = sa['email']

        # Sanitize resource name (handles emails starting with numbers)
        resource_name = sanitize_terraform_name(email, 'service_account')

        lines.append(f"""import {{
  to = google_service_account.{resource_name}
  id = "projects/{project_id}/serviceAccounts/{email}"
}}
""")

    # Cloud SQL imports
    for db in selected_resources.get('cloud_sql', []):
        if not db.get('_create'):
            db_name = db['name']
            module_name = db_name.replace('-', '_')

            lines.append(f"""import {{
  to = module.{module_name}.google_sql_database_instance.instance
  id = "{db_name}"
}}
""")

    (output_dir / 'imports.tf').write_text('\n'.join(lines))


def generate_outputs_tf(client: str, project: str, selected_resources: Dict[str, List], output_dir: Path):
    """Generate outputs.tf"""
    lines = ["# Outputs\n"]

    # Cloud Run URLs
    for service in selected_resources.get('cloud_run', []):
        service_name = service['name']
        module_name = service_name.replace('-', '_')

        lines.append(f"""
output "{module_name}_url" {{
  description = "URL for {service_name}"
  value       = module.{module_name}.service_url
}}
""")

    # Database connection info
    for db in selected_resources.get('cloud_sql', []):
        db_name = db['name']
        module_name = db_name.replace('-', '_')

        lines.append(f"""
output "{module_name}_connection" {{
  description = "Connection name for {db_name}"
  value       = module.{module_name}.connection_name
  sensitive   = true
}}
""")

    (output_dir / 'outputs.tf').write_text('\n'.join(lines))


# Placeholder implementations - will be expanded with actual module configs

def generate_terraform_for_new_resources(resources: Dict) -> str:
    """Generate Terraform for resources marked as _create"""
    # TODO: Implement based on modules
    return ""

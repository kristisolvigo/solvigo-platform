"""
Terraform code generator - creates Terraform configurations from selected resources
"""
from pathlib import Path
from typing import Dict, List
from jinja2 import Template
from rich.console import Console
import shutil

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

    Copies from CLI's terraform_templates/ to client repo's .terraform-modules/
    """
    # Get CLI's terraform_templates directory
    cli_templates_dir = Path(__file__).parent.parent / 'terraform_templates'

    if not cli_templates_dir.exists():
        console.print(f"[yellow]⚠ Terraform templates not found at {cli_templates_dir}[/yellow]")
        return False

    # Copy to client repo
    modules_dir = output_dir.parent / '.terraform-modules'

    if modules_dir.exists():
        console.print(f"  [dim]Terraform modules already exist at {modules_dir}[/dim]")
        return True

    try:
        console.print(f"  [cyan]Copying Terraform modules...[/cyan]")
        shutil.copytree(cli_templates_dir, modules_dir)
        console.print(f"  [green]✓ Modules copied to .terraform-modules/[/green]")
        return True
    except Exception as e:
        console.print(f"  [yellow]⚠ Could not copy modules: {e}[/yellow]")
        return False


def generate_terraform_config(
    client: str,
    project: str,
    selected_resources: Dict[str, List],
    output_dir: Path
) -> bool:
    """
    Generate Terraform configuration from selected resources.

    Args:
        client: Client name
        project: Project name
        selected_resources: Dict of selected resources
        output_dir: Output directory for Terraform files

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
        generate_variables_tf(client, project, output_dir)
        console.print("  ✓ Created variables.tf")

        # Generate main.tf with provider
        generate_main_tf(client, project, output_dir)
        console.print("  ✓ Created main.tf")

        # Generate Cloud Run resources
        if selected_resources.get('cloud_run'):
            generate_cloud_run_tf(client, project, selected_resources['cloud_run'], output_dir)
            console.print("  ✓ Created cloud-run.tf")

        # Generate database resources
        if selected_resources.get('cloud_sql'):
            generate_cloud_sql_tf(client, project, selected_resources['cloud_sql'], output_dir)
            console.print("  ✓ Created database-sql.tf")

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

        # Generate service accounts
        if selected_resources.get('service_accounts'):
            generate_service_accounts_tf(client, project, selected_resources['service_accounts'], output_dir)
            console.print("  ✓ Created service-accounts.tf")

        # Generate import blocks
        generate_imports_tf(client, project, selected_resources, output_dir)
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


def generate_variables_tf(client: str, project: str, output_dir: Path):
    """Generate variables.tf"""
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
    client      = "{{ client }}"
    project     = "{{ project }}"
    environment = "prod"
    managed_by  = "terraform"
    cost_center = "client-billable"
  }
}
""")

    # Try to infer project_id
    project_id = f"{client}-{project}-prod"

    content = template.render(
        client=client,
        project=project,
        project_id=project_id
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


def generate_cloud_run_tf(client: str, project: str, services: List[Dict], output_dir: Path, append: bool = False):
    """
    Generate Cloud Run service configurations.

    Args:
        append: If True, append to existing file instead of overwriting
    """
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
                module_code = generate_cloud_run_module(client, project, service)
            else:
                module_code = generate_cloud_run_import_module(client, project, service)

            with open(file_path, 'a') as f:
                f.write("\n\n")
                f.write(module_code)
    else:
        # Normal mode - generate full file
        lines = ["# Cloud Run Services\n"]

        for service in services:
            if service.get('_create'):
                # New service - use module
                lines.append(generate_cloud_run_module(client, project, service))
            else:
                # Existing service - use module with import
                lines.append(generate_cloud_run_import_module(client, project, service))

        file_path.write_text('\n'.join(lines))


def generate_cloud_run_module(client: str, project: str, service: Dict) -> str:
    """Generate module configuration for Cloud Run service"""
    service_name = service['name']
    service_type = service.get('type', 'backend')
    region = service.get('region', 'europe-north2')

    template = Template("""
# {{ service_name }} ({{ service_type }})
# Note: Initial deployment uses placeholder image (gcr.io/cloudrun/hello)
# Your CI/CD pipeline will deploy the real application image
# Terraform manages infrastructure; CI/CD manages deployments
module "{{ module_name }}" {
  source = "../.terraform-modules/cloud-run-app"

  project_id   = var.project_id
  service_name = "{{ service_name }}"
  region       = "{{ region }}"

  # image defaults to gcr.io/cloudrun/hello for initial deployment
  # CI/CD will update to real image via Cloud Build
  # See .terraform-modules/cloud-run-app/README.md for details

  labels = local.labels
}
""")

    module_name = service_name.replace('-', '_')

    return template.render(
        service_name=service_name,
        service_type=service_type,
        module_name=module_name,
        region=region
    )


def generate_cloud_run_import_module(client: str, project: str, service: Dict) -> str:
    """Generate module configuration for existing Cloud Run service with import"""
    # For now, same as new service
    # Import block will be in imports.tf
    return generate_cloud_run_module(client, project, service)


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
    db_name = db['name']
    db_version = db.get('database_version', 'POSTGRES_15')
    tier = db.get('tier', 'db-g1-small')

    template = Template("""
# Cloud SQL: {{ db_name }}
module "{{ module_name }}" {
  source = "../.terraform-modules/database-cloudsql"

  project_id       = var.project_id
  instance_name    = "{{ db_name }}"
  database_version = "{{ db_version }}"
  tier             = "{{ tier }}"
  region           = var.region

  enable_backups = {{ enable_backups }}

  labels = local.labels
}
""")

    module_name = db_name.replace('-', '_')
    enable_backups = str(db.get('backups', True)).lower()

    return template.render(
        db_name=db_name,
        module_name=module_name,
        db_version=db_version,
        tier=tier,
        enable_backups=enable_backups
    )


def generate_cloud_sql_import_module(client: str, project: str, db: Dict) -> str:
    """Generate module for existing Cloud SQL with import"""
    return generate_cloud_sql_module(client, project, db)


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
  source = "../.terraform-modules/database-firestore"

  project_id = var.project_id
  location   = "{{ location }}"
  mode       = "{{ mode }}"

  labels = local.labels
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
  source = "../.terraform-modules/storage-bucket"

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


def generate_service_accounts_tf(client: str, project: str, accounts: List[Dict], output_dir: Path, append: bool = False):
    """Generate service account configurations"""
    lines = ["# Service Accounts\n"]

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


def generate_imports_tf(client: str, project: str, selected_resources: Dict[str, List], output_dir: Path, append: bool = False):
    """Generate import blocks for existing resources"""
    lines = ["# Terraform Import Blocks\n"]
    lines.append("# These import blocks will bring existing GCP resources into Terraform state\n\n")

    project_id = f"{client}-{project}-prod"  # TODO: Get actual project ID

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

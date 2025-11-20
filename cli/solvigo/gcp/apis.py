"""
GCP API management - enable and track APIs for discovery and Terraform
"""
import subprocess
import json
from typing import List, Set
from rich.console import Console
from rich.progress import Progress

console = Console()


# APIs required for resource discovery
DISCOVERY_APIS = {
    'run.googleapis.com': 'Cloud Run',
    'sqladmin.googleapis.com': 'Cloud SQL',
    'storage.googleapis.com': 'Cloud Storage',
    'secretmanager.googleapis.com': 'Secret Manager',
    'iam.googleapis.com': 'IAM',
    'compute.googleapis.com': 'Compute Engine (for VPC)',
    'firestore.googleapis.com': 'Firestore',
}

# Additional APIs that might be in use
COMMON_APIS = {
    'aiplatform.googleapis.com': 'Vertex AI',
    'bigquery.googleapis.com': 'BigQuery',
    'pubsub.googleapis.com': 'Pub/Sub',
    'translate.googleapis.com': 'Translation API',
    'vision.googleapis.com': 'Vision API',
    'language.googleapis.com': 'Natural Language API',
    'cloudtasks.googleapis.com': 'Cloud Tasks',
    'cloudscheduler.googleapis.com': 'Cloud Scheduler',
}

# APIs required for CI/CD (Cloud Build)
CICD_APIS = {
    'cloudbuild.googleapis.com': 'Cloud Build',
    'artifactregistry.googleapis.com': 'Artifact Registry',
    'containerregistry.googleapis.com': 'Container Registry',
}


def get_enabled_apis(project_id: str) -> Set[str]:
    """
    Get list of currently enabled APIs in a project.

    Args:
        project_id: GCP project ID

    Returns:
        Set of enabled API names
    """
    try:
        result = subprocess.run(
            [
                'gcloud', 'services', 'list',
                '--enabled',
                f'--project={project_id}',
                '--format=json',
                '--verbosity=error'
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )

        if result.returncode != 0:
            return set()

        services = json.loads(result.stdout) if result.stdout else []
        return {service.get('config', {}).get('name', '') for service in services}

    except Exception:
        return set()


def enable_apis(project_id: str, apis: List[str]) -> bool:
    """
    Enable multiple APIs in a project.

    Args:
        project_id: GCP project ID
        apis: List of API names to enable

    Returns:
        True if successful, False otherwise
    """
    if not apis:
        return True

    console.print(f"\n[cyan]Enabling {len(apis)} APIs...[/cyan]")

    try:
        # Enable all APIs at once
        result = subprocess.run(
            [
                'gcloud', 'services', 'enable',
                *apis,
                f'--project={project_id}'
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=300  # API enablement can take time
        )

        if result.returncode == 0:
            console.print(f"[green]✓ APIs enabled successfully[/green]\n")
            return True
        else:
            console.print(f"[red]✗ Failed to enable APIs[/red]")
            console.print(f"[dim]{result.stderr}[/dim]\n")
            return False

    except subprocess.TimeoutExpired:
        console.print("[red]✗ API enablement timed out[/red]\n")
        return False
    except Exception as e:
        console.print(f"[red]✗ Error enabling APIs: {e}[/red]\n")
        return False


def ensure_discovery_apis(project_id: str) -> dict:
    """
    Ensure required APIs for discovery are enabled.

    Args:
        project_id: GCP project ID

    Returns:
        dict with:
            - enabled_apis: Set of APIs that were already enabled
            - newly_enabled: List of APIs that were just enabled
            - failed: List of APIs that failed to enable
    """
    from rich.table import Table
    from solvigo.ui.prompts import confirm_action

    console.print(f"\n[cyan]Checking required APIs for {project_id}...[/cyan]")

    # Get currently enabled APIs
    enabled = get_enabled_apis(project_id)

    # Check which discovery APIs are missing
    missing = []
    for api, name in DISCOVERY_APIS.items():
        if api not in enabled:
            missing.append((api, name))

    if not missing:
        console.print("[green]✓ All required APIs are already enabled[/green]\n")
        return {
            'enabled_apis': enabled,
            'newly_enabled': [],
            'failed': []
        }

    # Show missing APIs
    console.print(f"\n[yellow]Found {len(missing)} APIs that need to be enabled:[/yellow]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("API")
    table.add_column("Service")

    for api, name in missing:
        table.add_row(api, name)

    console.print(table)
    console.print()

    # Ask for confirmation
    if not confirm_action(
        f"Enable these {len(missing)} APIs? (Required for resource discovery)",
        default=True
    ):
        console.print("[yellow]⚠ Skipping API enablement. Discovery may be incomplete.[/yellow]\n")
        return {
            'enabled_apis': enabled,
            'newly_enabled': [],
            'failed': []
        }

    # Enable all APIs at once (faster than one-by-one)
    apis_to_enable = [api for api, _ in missing]

    console.print(f"\n[cyan]Enabling {len(apis_to_enable)} APIs (this may take 1-2 minutes)...[/cyan]")

    try:
        result = subprocess.run(
            [
                'gcloud', 'services', 'enable',
                *apis_to_enable,  # Enable all at once
                f'--project={project_id}'
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=300  # 3 minutes for all APIs
        )

        if result.returncode == 0:
            console.print("[green]✓ APIs enabled successfully[/green]\n")
            console.print("[dim]Waiting for APIs to propagate...[/dim]")

            # Wait for APIs to propagate
            import time
            time.sleep(5)

            return {
                'enabled_apis': enabled,
                'newly_enabled': apis_to_enable,
                'failed': []
            }
        else:
            console.print(f"[red]✗ Failed to enable some APIs[/red]")
            console.print(f"[dim]{result.stderr}[/dim]\n")
            return {
                'enabled_apis': enabled,
                'newly_enabled': [],
                'failed': apis_to_enable
            }

    except subprocess.TimeoutExpired:
        console.print("[yellow]⚠ API enablement timed out after 3 minutes[/yellow]")
        console.print("[dim]APIs may still be enabling in the background...[/dim]\n")
        return {
            'enabled_apis': enabled,
            'newly_enabled': [],
            'failed': apis_to_enable
        }
    except Exception as e:
        console.print(f"[red]✗ Error enabling APIs: {e}[/red]\n")
        return {
            'enabled_apis': enabled,
            'newly_enabled': [],
            'failed': apis_to_enable
        }


def get_project_apis_for_terraform(project_id: str) -> List[str]:
    """
    Get all non-default APIs that should be included in Terraform.

    Excludes default/automatic APIs like cloudapis.com.

    Args:
        project_id: GCP project ID

    Returns:
        List of API names to include in Terraform
    """
    enabled = get_enabled_apis(project_id)

    # Default APIs that are auto-enabled (skip these)
    default_apis = {
        'cloudapis.googleapis.com',
        'clouddebugger.googleapis.com',
        'cloudtrace.googleapis.com',
        'datastore.googleapis.com',
        'logging.googleapis.com',
        'monitoring.googleapis.com',
        'servicemanagement.googleapis.com',
        'serviceusage.googleapis.com',
        'sql-component.googleapis.com',
        'storage-api.googleapis.com',
        'storage-component.googleapis.com',
    }

    # Return only non-default APIs
    return sorted([api for api in enabled if api not in default_apis])

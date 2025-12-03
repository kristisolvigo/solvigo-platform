"""Bootstrap essential GCP resources before Terraform runs"""
import subprocess
from pathlib import Path
from typing import Tuple
from rich.console import Console

console = Console()

# Platform project configuration
PLATFORM_PROJECT_NUMBER = "430162142300"  # solvigo-platform-prod


def run_gcloud(cmd: list) -> Tuple[bool, str]:
    """Run gcloud command and return (success, output)"""
    try:
        result = subprocess.run(
            ['gcloud'] + cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr


def create_state_bucket(project_id: str, region: str, bucket_name: str) -> bool:
    """Create Terraform state bucket if it doesn't exist"""
    console.print(f"[cyan]Checking state bucket: {bucket_name}[/cyan]")

    # Check if bucket exists
    success, output = run_gcloud([
        'storage', 'buckets', 'describe', f'gs://{bucket_name}',
        '--project', project_id
    ])

    if success:
        console.print(f"[green]✓ State bucket exists[/green]")
        return True

    # Create bucket
    console.print(f"[cyan]Creating state bucket...[/cyan]")
    success, output = run_gcloud([
        'storage', 'buckets', 'create', f'gs://{bucket_name}',
        '--project', project_id,
        '--location', region,
        '--uniform-bucket-level-access'
    ])

    if success:
        # Enable versioning
        run_gcloud([
            'storage', 'buckets', 'update', f'gs://{bucket_name}',
            '--versioning'
        ])
        console.print(f"[green]✓ Created state bucket[/green]")
        return True
    else:
        console.print(f"[red]✗ Failed to create state bucket: {output}[/red]")
        return False


def create_deployer_sa(project_id: str, sa_name: str = "deployer") -> Tuple[bool, str]:
    """Create deployer service account if it doesn't exist"""
    sa_email = f"{sa_name}@{project_id}.iam.gserviceaccount.com"
    console.print(f"[cyan]Checking deployer SA: {sa_email}[/cyan]")

    # Check if SA exists
    success, output = run_gcloud([
        'iam', 'service-accounts', 'describe', sa_email,
        '--project', project_id
    ])

    sa_exists = success

    if not sa_exists:
        # Create SA
        console.print(f"[cyan]Creating deployer SA...[/cyan]")
        success, output = run_gcloud([
            'iam', 'service-accounts', 'create', sa_name,
            '--project', project_id,
            '--display-name', 'Cloud Build Deployer',
            '--description', 'Service account for deploying services via Cloud Build'
        ])

        if not success:
            console.print(f"[red]✗ Failed to create deployer SA: {output}[/red]")
            return False, sa_email
    else:
        console.print(f"[green]✓ Deployer SA exists[/green]")

    # Grant/ensure permissions (whether SA was just created or already existed)
    console.print(f"[cyan]Ensuring permissions are configured...[/cyan]")
    roles = [
        'roles/run.admin',
        'roles/secretmanager.secretAccessor',
        'roles/artifactregistry.writer'
    ]

    for role in roles:
        run_gcloud([
            'projects', 'add-iam-policy-binding', project_id,
            '--member', f'serviceAccount:{sa_email}',
            '--role', role,
            '--condition=None'
        ])

    # Allow Cloud Build to impersonate this SA
    run_gcloud([
        'iam', 'service-accounts', 'add-iam-policy-binding', sa_email,
        '--member', f'serviceAccount:{project_id}@cloudbuild.gserviceaccount.com',
        '--role', 'roles/iam.serviceAccountUser',
        '--project', project_id
    ])

    # Allow platform registry-api SA to create Cloud Build triggers that use this SA
    # Only needs serviceAccountUser (not serviceAccountTokenCreator)
    run_gcloud([
        'iam', 'service-accounts', 'add-iam-policy-binding', sa_email,
        '--member', 'serviceAccount:registry-api@solvigo-platform-prod.iam.gserviceaccount.com',
        '--role', 'roles/iam.serviceAccountUser',
        '--project', project_id
    ])

    # Allow platform Cloud Build SA to execute builds using this SA
    # Needs both roles for impersonation during build execution
    run_gcloud([
        'iam', 'service-accounts', 'add-iam-policy-binding', sa_email,
        '--member', f'serviceAccount:{PLATFORM_PROJECT_NUMBER}@cloudbuild.gserviceaccount.com',
        '--role', 'roles/iam.serviceAccountUser',
        '--project', project_id
    ])

    run_gcloud([
        'iam', 'service-accounts', 'add-iam-policy-binding', sa_email,
        '--member', f'serviceAccount:{PLATFORM_PROJECT_NUMBER}@cloudbuild.gserviceaccount.com',
        '--role', 'roles/iam.serviceAccountTokenCreator',
        '--project', project_id
    ])

    # Grant project-level serviceAccountUser permission to registry-api
    # This allows registry-api to create Cloud Build triggers that use this project's service accounts
    run_gcloud([
        'projects', 'add-iam-policy-binding', project_id,
        '--member', 'serviceAccount:registry-api@solvigo-platform-prod.iam.gserviceaccount.com',
        '--role', 'roles/iam.serviceAccountUser'
    ])

    console.print(f"[green]✓ Created deployer SA with permissions[/green]")
    return True, sa_email


def grant_vpc_connector_permission(project_id: str, host_project: str = "solvigo-platform-prod") -> bool:
    """
    Grant Cloud Run service agent VPC connector permission in host project.

    Args:
        project_id: Client GCP project ID
        host_project: Host project ID for Shared VPC (default: solvigo-platform-prod)

    Returns:
        True if permission granted successfully, False otherwise
    """
    console.print(f"[cyan]Granting VPC connector permissions...[/cyan]")

    # Get project number
    success, output = run_gcloud([
        'projects', 'describe', project_id,
        '--format', 'value(projectNumber)'
    ])

    if not success:
        console.print(f"[red]✗ Failed to get project number[/red]")
        return False

    project_number = output.strip()
    service_agent = f"service-{project_number}@serverless-robot-prod.iam.gserviceaccount.com"

    # Grant VPC access permission in host project
    success, output = run_gcloud([
        'projects', 'add-iam-policy-binding', host_project,
        '--member', f'serviceAccount:{service_agent}',
        '--role', 'roles/vpcaccess.user',
        '--condition=None'
    ])

    if success or "ALREADY_EXISTS" in output:
        console.print(f"[green]✓ VPC connector permissions granted[/green]")
        return True

    console.print(f"[yellow]⚠ Failed - run manually:[/yellow]")
    console.print(f"[dim]gcloud projects add-iam-policy-binding {host_project} \\[/dim]")
    console.print(f"[dim]  --member='serviceAccount:{service_agent}' \\[/dim]")
    console.print(f"[dim]  --role='roles/vpcaccess.user'[/dim]")
    return False


def bootstrap_infrastructure(
    project_id: str,
    region: str,
    bucket_name: str,
    grant_vpc_access: bool = True
) -> dict:
    """
    Bootstrap all essential resources.

    Args:
        project_id: GCP project ID
        region: GCP region
        bucket_name: Terraform state bucket name
        grant_vpc_access: Whether to grant VPC connector permissions (default: True)

    Returns:
        dict with results of each bootstrap operation
    """
    console.print("\n[cyan]═══ Bootstrapping Essential Resources ═══[/cyan]\n")

    results = {}

    # 1. Create state bucket
    results['state_bucket'] = create_state_bucket(project_id, region, bucket_name)

    # 2. Create deployer SA
    success, sa_email = create_deployer_sa(project_id)
    results['deployer_sa'] = success
    results['deployer_sa_email'] = sa_email

    # 3. Grant VPC connector permissions (if enabled)
    if grant_vpc_access:
        results['vpc_access'] = grant_vpc_connector_permission(project_id)
    else:
        results['vpc_access'] = True  # Not attempted, mark as success

    if not all([results['state_bucket'], results['deployer_sa'], results.get('vpc_access', True)]):
        console.print("\n[yellow]⚠ Some bootstrap operations failed[/yellow]")
        console.print("[dim]You may need to create these resources manually[/dim]\n")
    else:
        console.print("\n[green]✓ Bootstrap complete[/green]\n")

    return results

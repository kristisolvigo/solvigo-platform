"""
Initialize new project - create infrastructure and scaffold code
"""
import os
import subprocess
from pathlib import Path
from rich.console import Console
from rich.table import Table

from solvigo.ui.prompts import text_input, select_option, confirm_action
from solvigo.admin.client import AdminClient
from solvigo.gcp.discovery import verify_gcp_project_access
from solvigo.terraform.generator import generate_terraform_config
from solvigo.ui.cicd_prompts import (
    prompt_cicd_setup,
    prompt_application_type,
    prompt_repository_location,
    prompt_dockerfile_location,
    prompt_service_name,
    prompt_github_repo_url,
    prompt_environments,
    show_cicd_summary,
    confirm_cicd_setup,
    get_platform_project_id,
    get_github_connection_id
)

console = Console()


def create_project(client: str, project: str, environment: str, stack: str,
                  database: str, new_client: bool, dry_run: bool):
    """
    Create a new project (non-interactive version).
    """
    # This function is kept for compatibility but the main logic is in interactive_create_project
    # or should be refactored to be shared. For now, we focus on interactive flow.
    pass


def generate_infrastructure_interactive(context: dict) -> bool:
    """
    Generate infrastructure for an existing registered project.

    Args:
        context: Project context dict with keys:
            - client: Client name
            - project: Project ID
            - gcp_project_id: GCP project ID
            - github_url: GitHub repository URL
            - path: Local repository path

    Returns:
        dict: Generated infrastructure data with keys:
            - success: bool - True if generation succeeded
            - services: list - Service configurations
            - environments: list - Environment names
            - app_type: str - Application type
            - database_choice: str - Database selection
            - bucket_name: str - Terraform state bucket name
            - github_repo_url: str - GitHub repository URL
            - enable_vertex_ai: bool - Vertex AI enabled
            - enable_secret_manager: bool - Secret Manager enabled
            - client_slug: str - Client slug
            - project_slug: str - Project slug
    """
    from pathlib import Path

    # Extract context
    client_name = context.get('client', '')
    project_id = context.get('project', '')
    gcp_project_id = context.get('gcp_project_id', '')
    github_url = context.get('github_url', '')
    repo_path = Path(context.get('path', '.'))
    client_subdomain = context.get('client_subdomain')
    project_subdomain = context.get('project_subdomain')

    # Derive slugs from project_id if available
    if '-' in project_id:
        parts = project_id.split('-')
        client_slug = parts[0]
        project_slug = '-'.join(parts[1:])
        project_name = project_slug.replace('-', ' ').title()
    else:
        client_slug = client_name.lower().replace(' ', '-')
        project_slug = project_id.lower().replace(' ', '-')
        project_name = project_id

    console.print("[bold]Let's configure infrastructure for your project![/bold]\n")

    # Validate GCP project access
    console.print(f"[cyan]Verifying access to {gcp_project_id}...[/cyan]")
    if not verify_gcp_project_access(gcp_project_id):
        console.print(f"[red]✗ Cannot access project {gcp_project_id}[/red]")
        console.print("[yellow]Make sure you are authenticated and have permissions.[/yellow]")
        return {'success': False}
    console.print(f"[green]✓ Project accessible[/green]\n")

    # Validate/prompt for repository location
    if not repo_path.exists():
        console.print(f"[yellow]Repository path not found: {repo_path}[/yellow]")
        repo_path = prompt_repository_location(client_name, project_name)

    # 1. Application Type & Dockerfiles
    app_type = prompt_application_type()

    services = []
    if app_type in ['backend', 'fullstack']:
        dockerfile = prompt_dockerfile_location('backend', repo_path)
        service_name = prompt_service_name('backend', f"{project_slug}-backend")
        services.append({
            'type': 'backend',
            'name': service_name,
            'dockerfile': dockerfile,
            '_create': True
        })

    if app_type in ['frontend', 'fullstack']:
        dockerfile = prompt_dockerfile_location('frontend', repo_path)
        service_name = prompt_service_name('frontend', f"{project_slug}-frontend")
        services.append({
            'type': 'frontend',
            'name': service_name,
            'dockerfile': dockerfile,
            '_create': True
        })

    # 2. Database
    database_choice = select_option(
        "Database:",
        choices=[
            "PostgreSQL (Cloud SQL)",
            "MySQL (Cloud SQL)",
            "Firestore",
            "Both SQL + Firestore",
            "None"
        ]
    )

    selected_resources = {
        'cloud_run': services,
        'cloud_sql': [],
        'firestore': [],
        'storage': [],
        'secrets': [],
        'service_accounts': []
    }

    if "PostgreSQL" in database_choice or "Both" in database_choice:
        selected_resources['cloud_sql'].append({
            'name': f"{project_slug}-db",
            'database_version': 'POSTGRES_15',
            'tier': 'db-f1-micro',
            'backups': True,
            '_create': True
        })

    if "MySQL" in database_choice:
        selected_resources['cloud_sql'].append({
            'name': f"{project_slug}-db",
            'database_version': 'MYSQL_8_0',
            'tier': 'db-f1-micro',
            'backups': True,
            '_create': True
        })

    if "Firestore" in database_choice or "Both" in database_choice:
        selected_resources['firestore'].append({
            'location': 'europe-north1',
            'mode': 'FIRESTORE_NATIVE',
            '_create': True
        })

    # 3. Vertex AI Enablement
    enable_vertex_ai = confirm_action(
        "Enable Vertex AI API? (for ML/AI features)",
        default=False
    )

    if enable_vertex_ai:
        selected_resources['apis'] = selected_resources.get('apis', [])
        selected_resources['apis'].append('aiplatform.googleapis.com')

    # 4. Secret Manager Enablement
    enable_secret_manager = confirm_action(
        "Enable Secret Manager API? (for application secrets)",
        default=False
    )

    if enable_secret_manager:
        selected_resources['apis'] = selected_resources.get('apis', [])
        selected_resources['apis'].append('secretmanager.googleapis.com')

    # 5. CI/CD & Environments
    environments = prompt_environments()

    # Use github_url from context or prompt for it
    if not github_url:
        github_repo_url = prompt_github_repo_url(client_name, project_name)
    else:
        # Confirm the GitHub URL
        confirmed_url = text_input(
            f"GitHub repository URL:",
            default=github_url
        )
        github_repo_url = confirmed_url if confirmed_url else github_url

    # 6. Summary & Confirmation
    console.print("\n" + "─" * 64)
    console.print("[bold]Summary:[/bold]\n")
    console.print(f"  Client:       {client_name}")
    console.print(f"  Project:      {project_name}")
    console.print(f"  GCP Project:  {gcp_project_id}")
    console.print(f"  Stack:        {app_type}")
    console.print(f"  Database:     {database_choice}")
    console.print(f"  Vertex AI:    {'Enabled' if enable_vertex_ai else 'Disabled'}")
    console.print(f"  Secret Mgr:   {'Enabled' if enable_secret_manager else 'Disabled'}")
    console.print(f"  Environments: {', '.join(environments)}")
    console.print("─" * 64 + "\n")

    if not confirm_action("Generate infrastructure with these settings?", default=True):
        console.print("\n[yellow]Cancelled.[/yellow]\n")
        return {'success': False}

    # 7. Execution
    console.print("\n[cyan]🚀 Generating infrastructure...[/cyan]\n")

    # 7.1 Setup GCS State Bucket
    bucket_name = f"{client_slug}-terraform-state"
    console.print(f"[dim]Ensuring Terraform state bucket exists: {bucket_name}[/dim]")
    try:
        # Check if exists
        check = subprocess.run(
            ['gcloud', 'storage', 'buckets', 'describe', f'gs://{bucket_name}'],
            capture_output=True
        )
        if check.returncode != 0:
            # Create
            subprocess.run(
                ['gcloud', 'storage', 'buckets', 'create', f'gs://{bucket_name}',
                 '--project', gcp_project_id, '--location', 'europe-north1'],
                check=True, capture_output=True
            )
            console.print(f"[green]✓ Created state bucket: {bucket_name}[/green]")
        else:
            console.print(f"[green]✓ State bucket exists[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed to setup state bucket: {e}[/red]")
        console.print("[yellow]You may need to create it manually.[/yellow]")

    # 7.2 Connect to Shared VPC
    host_project = "solvigo-platform-prod"
    console.print(f"[dim]Connecting to Shared VPC (Host: {host_project})...[/dim]")
    try:
        # Enable compute API first
        subprocess.run(
            ['gcloud', 'services', 'enable', 'compute.googleapis.com', '--project', gcp_project_id],
            check=True, capture_output=True
        )

        # Associate project
        subprocess.run(
            ['gcloud', 'compute', 'shared-vpc', 'associated-projects', 'add', gcp_project_id,
             '--host-project', host_project],
            check=True, capture_output=True
        )
        console.print(f"[green]✓ Connected to Shared VPC[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Could not connect to Shared VPC (might already be connected or lack permissions): {e}[/yellow]")

    # 7.3 Generate Terraform
    terraform_dir = repo_path / 'terraform'
    cicd_dir = repo_path / 'cicd'

    terraform_dir.mkdir(parents=True, exist_ok=True)
    cicd_dir.mkdir(parents=True, exist_ok=True)

    if not gcp_project_id:
        console.print(f"[red]✗ No GCP project ID in context[/red]")
        return {'success': False}

    if generate_terraform_config(
        client_name,
        project_name,
        selected_resources,
        terraform_dir,
        gcp_project_id,
        client_subdomain=client_subdomain,
        project_subdomain=project_subdomain
    ):
        console.print(f"[green]✓ Generated Terraform config in {terraform_dir}[/green]")
    else:
        console.print(f"[red]✗ Failed to generate Terraform config[/red]")
        return {'success': False}

    # 7.3.5 Bootstrap Essential Resources
    from solvigo.utils.bootstrap import bootstrap_infrastructure

    # Default region for European deployments
    region = 'europe-north1'

    bootstrap_results = bootstrap_infrastructure(
        project_id=gcp_project_id,
        region=region,
        bucket_name=bucket_name
    )

    if not bootstrap_results['deployer_sa']:
        console.print("[red]✗ Failed to create deployer SA[/red]")
        console.print("[yellow]Cloud Build triggers will fail without deployer SA[/yellow]")
        # Continue anyway - user can fix manually

    # 7.4 Generate CI/CD Files
    has_database = bool(selected_resources.get('cloud_sql') or selected_resources.get('firestore'))
    platform_project_id = get_platform_project_id()
    github_connection_id = get_github_connection_id(dev_mode=context.get('dev', False))

    if github_connection_id:
        from solvigo.terraform.cicd_generator import generate_all_cicd_files

        cicd_success = generate_all_cicd_files(
            client=client_name,
            project=project_name,
            platform_project_id=platform_project_id,
            client_project_id=gcp_project_id,
            github_connection_id=github_connection_id,
            github_repo_url=github_repo_url,
            services=services,
            environments=environments,
            terraform_dir=terraform_dir,
            app_dir=cicd_dir,
            has_database=has_database
        )
        if cicd_success:
            console.print(f"[green]✓ Generated CI/CD config in {cicd_dir}[/green]")

            # 7.5 Register Cloud Build triggers with Admin API
            console.print("\n[cyan]🔧 Setting up Cloud Build triggers...[/cyan]")

            try:
                # Import Admin client
                from solvigo.admin.client import AdminClient

                # Build environment configurations
                env_configs = []
                for env_name in environments:
                    # Determine trigger patterns based on environment
                    if env_name in ['dev', 'staging']:
                        env_config = {
                            'name': env_name,
                            'branch_pattern': '^main$',
                            'tag_pattern': None
                        }
                    elif env_name == 'prod':
                        env_config = {
                            'name': env_name,
                            'branch_pattern': None,
                            'tag_pattern': '^v.*'
                        }
                    else:
                        # Custom environment - default to branch-based
                        env_config = {
                            'name': env_name,
                            'branch_pattern': f'^{env_name}$',
                            'tag_pattern': None
                        }

                    # Add cloudbuild_file (not used by new API but kept for compatibility)
                    env_config['cloudbuild_file'] = f"cicd/cloudbuild-backend.yaml"
                    env_configs.append(env_config)

                # Build service configurations
                service_configs = []
                for service in services:
                    service_configs.append({
                        'name': service['name'],
                        'type': service['type'],
                        'cloudbuild_file': f"cicd/cloudbuild-{service['type']}.yaml"
                    })

                # Call Admin API to create triggers
                admin_client = AdminClient(dev_mode=context.get('dev', False))

                trigger_response = admin_client.create_build_triggers(
                    project_id=f"{client_slug}-{project_slug}",
                    trigger_config={
                        'github_repo_url': github_repo_url,
                        'services': service_configs,
                        'environments': env_configs
                    }
                )

                console.print(f"[green]✓ Created {len(trigger_response['triggers'])} Cloud Build triggers[/green]")

                # Show created triggers
                for trigger in trigger_response['triggers']:
                    console.print(f"  • {trigger['service']}-{trigger['environment']}")

            except Exception as e:
                console.print(f"[yellow]⚠ Failed to create Cloud Build triggers: {e}[/yellow]")
                console.print("[dim]You can create them manually later via the Admin API[/dim]")
        else:
            console.print(f"[yellow]⚠ CI/CD generation had issues (check logs)[/yellow]")
    else:
        console.print("[yellow]⚠ Skipping CI/CD generation (missing GitHub connection ID)[/yellow]")

    # Return infrastructure data for Admin API registration
    return {
        'success': True,
        'services': services,
        'environments': environments,
        'app_type': app_type,
        'database_choice': database_choice,
        'bucket_name': bucket_name,
        'github_repo_url': github_repo_url,
        'enable_vertex_ai': enable_vertex_ai,
        'enable_secret_manager': enable_secret_manager,
        'client_slug': client_slug,
        'project_slug': project_slug
    }


def interactive_create_project():
    """
    Create a new project interactively.
    """
    console.print("[bold]Let's create a new project![/bold]\n")
    console.print("[dim]This wizard assumes you have a clean GCP project and owner access.[/dim]\n")

    # 1. Ask for GCP Project ID
    gcp_project_id = text_input("Enter existing GCP Project ID:")
    
    console.print(f"[cyan]Verifying access to {gcp_project_id}...[/cyan]")
    if not verify_gcp_project_access(gcp_project_id):
        console.print(f"[red]✗ Cannot access project {gcp_project_id}[/red]")
        console.print("[yellow]Make sure you are authenticated and have permissions.[/yellow]")
        return

    console.print(f"[green]✓ Project accessible[/green]\n")

    # 2. Client Selection
    # Note: init doesn't get context yet, so dev_mode isn't available here
    # TODO: Consider passing dev flag through init command
    registry = AdminClient()
    try:
        clients = registry.list_clients()
    except Exception as e:
        console.print(f"[yellow]⚠ Could not list clients: {e}[/yellow]")
        clients = []

    client_choices = [f"{c['name']} ({c['id']})" for c in clients]
    client_choices.append("➕ Create new client")

    client_choice = select_option("Select Client:", choices=client_choices)

    if client_choice == "➕ Create new client":
        client_name = text_input("New Client Name:")
        client_slug = client_name.lower().replace(' ', '-')
        client_id = client_slug
        client_subdomain = client_slug

        # Register client
        try:
            registry.register_client({
                'id': client_id,
                'name': client_name,
                'subdomain': client_subdomain
            })
            console.print(f"[green]✓ Client '{client_name}' registered[/green]\n")
        except Exception as e:
            console.print(f"[red]✗ Failed to register client: {e}[/red]")
            return
    else:
        # Use existing client - fetch full details to get subdomain
        client_id = client_choice.split('(')[1].rstrip(')')
        try:
            client_details = registry.get_client(client_id)
            client_name = client_details['name']
            client_subdomain = client_details['subdomain']
            client_slug = client_subdomain  # Use subdomain for backward compatibility
        except Exception as e:
            console.print(f"[red]✗ Failed to fetch client details: {e}[/red]")
            return

    # 3. Project Details
    project_name = text_input("Project Name:")
    project_slug = project_name.lower().replace(' ', '-')
    
    subdomain = text_input(f"Subdomain ({project_slug}.{client_subdomain}.solvigo.ai):", default=project_slug)

    # Build context for infrastructure generation
    context = {
        'client': client_name,
        'project': f"{client_subdomain}-{project_slug}",
        'gcp_project_id': gcp_project_id,
        'github_url': '',  # Will be prompted in shared function
        'path': str(prompt_repository_location(client_name, project_name))
    }

    # Call shared infrastructure generation function
    result = generate_infrastructure_interactive(context)

    if not result.get('success'):
        console.print("\n[red]✗ Infrastructure generation failed[/red]\n")
        return

    # Extract generated infrastructure details
    services = result['services']
    environments = result['environments']
    app_type = result['app_type']
    database_choice = result['database_choice']
    bucket_name = result['bucket_name']
    github_repo_url = result['github_repo_url']

    # 4. Register in Admin API
    console.print("[dim]Registering project in Admin API...[/dim]")
    try:
        # Prepare environment data
        env_data = []
        for env_name in environments:
            env_data.append({
                'project_id': f"{client_subdomain}-{project_slug}",
                'name': env_name,
                'database_instance': f"{project_slug}-db-{env_name}" if env_name != 'prod' else f"{project_slug}-db",
                'database_type': 'postgresql' if 'PostgreSQL' in database_choice else 'mysql' if 'MySQL' in database_choice else 'none',
                'auto_deploy': (env_name == 'staging'),
                'requires_approval': (env_name == 'prod')
            })

        # Prepare service data
        svc_data = []
        for svc in services:
            for env_name in environments:
                svc_suffix = f"-{env_name}" if env_name != 'prod' else ""
                svc_data.append({
                    'project_id': f"{client_subdomain}-{project_slug}",
                    'name': f"{svc['name']}{svc_suffix}",
                    'type': svc['type'],
                    'environment': env_name,
                    'cloud_run_service': f"{svc['name']}{svc_suffix}",
                    'cloud_run_region': 'europe-north1',
                    'dockerfile_path': svc['dockerfile'],
                    'cloudbuild_file': f"cicd/cloudbuild-{svc['type']}.yaml"
                })

        registry.register_project({
            'id': f"{client_subdomain}-{project_slug}",
            'client_id': client_id,
            'name': project_name,
            'subdomain': subdomain,
            'full_domain': f"{subdomain}.{client_subdomain}.solvigo.ai",
            'gcp_project_id': gcp_project_id,
            'github_repo': github_repo_url,
            'terraform_state_bucket': bucket_name,
            'project_type': app_type,
            'environments': env_data,
            'services': svc_data
        })
        console.print(f"[green]✓ Registered project in Admin API[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Failed to register project: {e}[/yellow]")

    console.print("\n[green bold]✨ Project initialization complete![/green bold]\n")
    console.print("Next steps:")
    console.print(f"  1. Review generated files in {context['path']}")
    console.print("  2. Commit and push to GitHub")
    console.print("  3. Run 'terraform init' and 'terraform apply' in terraform/ directory")

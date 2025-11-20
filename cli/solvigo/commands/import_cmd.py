"""
Import existing GCP project into Solvigo platform
"""
from rich.console import Console
from rich.table import Table

from solvigo.gcp.discovery import ResourceDiscovery, verify_gcp_project_access
from solvigo.ui.prompts import text_input, select_resources, confirm_action, select_option

console = Console()


def select_project_interactive(projects: list) -> str:
    """
    Let user select a project with search or pagination.

    Args:
        projects: List of project dicts

    Returns:
        Selected project ID
    """
    choice = select_option(
        "How would you like to find your project?",
        choices=[
            "🔍 Search by name",
            "📋 Browse all projects"
        ]
    )

    if "Search" in choice:
        # Search mode
        search_term = text_input(
            "Search for project (name or ID):"
        ).lower()

        # Filter projects
        matches = [
            p for p in projects
            if search_term in p['project_id'].lower() or search_term in p['name'].lower()
        ]

        if not matches:
            console.print(f"\n[yellow]No projects matching '{search_term}'[/yellow]\n")
            return None

        console.print(f"\n[green]Found {len(matches)} matching projects:[/green]\n")

        # Show matches
        if len(matches) <= 20:
            # Show all matches
            project_choices = [f"{p['project_id']} - {p['name']}" for p in matches]
            selected = select_option(
                "Select project:",
                choices=project_choices
            )
            return selected.split(' - ')[0]
        else:
            # Still too many, browse them
            return browse_projects_paginated(matches)
    else:
        # Browse mode with pagination
        return browse_projects_paginated(projects)


def browse_projects_paginated(projects: list, page_size: int = 15) -> str:
    """
    Browse projects with pagination.

    Args:
        projects: List of project dicts
        page_size: Number of projects per page

    Returns:
        Selected project ID
    """
    page = 0
    total_pages = (len(projects) + page_size - 1) // page_size

    while True:
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, len(projects))
        page_projects = projects[start_idx:end_idx]

        # Show current page
        console.print(f"\n[cyan]Page {page + 1} of {total_pages}[/cyan] (Projects {start_idx + 1}-{end_idx} of {len(projects)})\n")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Project ID", style="cyan")
        table.add_column("Name", style="white")

        for i, proj in enumerate(page_projects, start=1):
            table.add_row(
                str(start_idx + i),
                proj['project_id'],
                proj['name']
            )

        console.print(table)
        console.print()

        # Create choices for this page
        choices = [f"{p['project_id']} - {p['name']}" for p in page_projects]

        # Add navigation options
        if page > 0:
            choices.append("← Previous page")
        if page < total_pages - 1:
            choices.append("→ Next page")
        choices.append("🔍 Search instead")
        choices.append("❌ Cancel")

        selected = select_option(
            f"Select project (page {page + 1}/{total_pages}):",
            choices=choices
        )

        if "Previous" in selected:
            page -= 1
        elif "Next" in selected:
            page += 1
        elif "Search" in selected:
            return search_projects(projects)
        elif "Cancel" in selected:
            return None
        else:
            # Project selected
            return selected.split(' - ')[0]


def search_projects(projects: list) -> str:
    """
    Search for a project by name or ID.

    Args:
        projects: List of project dicts

    Returns:
        Selected project ID or None
    """
    search_term = text_input(
        "Search for project (name or ID):"
    ).lower()

    # Filter projects
    matches = [
        p for p in projects
        if search_term in p['project_id'].lower() or search_term in p['name'].lower()
    ]

    if not matches:
        console.print(f"\n[yellow]No projects matching '{search_term}'[/yellow]")
        retry = confirm_action("Try again?", default=True)
        if retry:
            return search_projects(projects)
        return None

    console.print(f"\n[green]Found {len(matches)} matching project(s):[/green]\n")

    if len(matches) == 1:
        # Only one match, auto-select
        proj = matches[0]
        console.print(f"  → {proj['project_id']} - {proj['name']}\n")
        if confirm_action("Use this project?", default=True):
            return proj['project_id']
        return search_projects(projects)

    # Multiple matches
    project_choices = [f"{p['project_id']} - {p['name']}" for p in matches]
    project_choices.append("🔍 Search again")

    selected = select_option(
        "Select project:",
        choices=project_choices
    )

    if "Search again" in selected:
        return search_projects(projects)

    return selected.split(' - ')[0]


def import_existing_project(gcp_project_id: str, client: str = None,
                           project: str = None, dry_run: bool = False):
    """
    Import existing GCP project (non-interactive).

    Args:
        gcp_project_id: GCP project ID to import
        client: Client name (optional, will prompt if not provided)
        project: Project name (optional, will prompt if not provided)
        dry_run: Whether to do dry run
    """
    console.print(f"\n[cyan]🔍 Importing GCP project: {gcp_project_id}[/cyan]\n")

    # Verify access
    if not verify_gcp_project_access(gcp_project_id):
        console.print(f"[red]✗ Cannot access project {gcp_project_id}[/red]")
        return

    console.print(f"[green]✓ Project accessible[/green]")

    # Get client/project if not provided
    if not client:
        client = text_input("Client name:")
    if not project:
        project = text_input("Project name:")

    # ═══ Folder Organization ═══
    # Get or create client folder and move project into it
    from solvigo.gcp.folders import get_or_create_client_folder, move_project_to_folder
    import os

    parent_folder_id = os.getenv('SOLVIGO_FOLDER_ID')
    client_folder_id = None

    if parent_folder_id:
        try:
            # Get or create client folder
            client_folder_id = get_or_create_client_folder(client, parent_folder_id)

            if client_folder_id:
                # Move project into client folder
                move_project_to_folder(gcp_project_id, client_folder_id)
            else:
                console.print("[dim]Continuing without folder organization...[/dim]\n")

        except Exception as e:
            console.print(f"[yellow]⚠ Folder management error: {e}[/yellow]")
            console.print("[dim]Continuing import...[/dim]\n")
    else:
        console.print("[dim]SOLVIGO_FOLDER_ID not set - skipping folder organization[/dim]\n")

    # Ensure required APIs are enabled for discovery
    from solvigo.gcp.apis import ensure_discovery_apis

    api_result = ensure_discovery_apis(gcp_project_id)

    # Discover resources
    discovery = ResourceDiscovery(gcp_project_id)
    resources = discovery.discover_all()

    # Track which APIs were enabled (for Terraform generation)
    resources['_enabled_apis'] = api_result['newly_enabled']
    resources['_all_apis'] = api_result['enabled_apis']

    # Select resources
    console.print("\n" + "─" * 64 + "\n")
    selected = select_resources(resources, client=client, project=project)

    if not selected or all(len(v) == 0 for v in selected.values()):
        console.print("\n[yellow]No resources selected.[/yellow]")
        return

    # Ask where to generate the infrastructure code
    from solvigo.ui.cicd_prompts import prompt_repository_location
    from pathlib import Path

    console.print("\n" + "═" * 64 + "\n")
    console.print("[cyan]Where should we generate the infrastructure code?[/cyan]\n")
    console.print("[dim]This should be your project's GitHub repository.[/dim]")
    console.print("[dim]We'll create terraform/ and cicd/ folders there.[/dim]\n")

    repo_path = prompt_repository_location(client, project)

    console.print(f"\n[green]✓ Will generate code in:[/green] {repo_path}\n")

    # Create output directories in the client repository
    terraform_dir = repo_path / 'terraform'
    cicd_dir = repo_path / 'cicd'

    terraform_dir.mkdir(parents=True, exist_ok=True)
    cicd_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"  [dim]Terraform:[/dim] {terraform_dir}")
    console.print(f"  [dim]CI/CD:[/dim] {cicd_dir}\n")

    # Generate Terraform configuration
    from solvigo.terraform.generator import generate_terraform_config

    if not generate_terraform_config(client, project, selected, terraform_dir):
        console.print("[red]✗ Failed to generate Terraform configuration[/red]\n")
        return

    # ═══ CI/CD Setup ═══
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

    console.print("\n" + "═" * 64 + "\n")

    if prompt_cicd_setup():
        # Get application type
        app_type = prompt_application_type()

        # Collect service configurations (using repo_path from above)
        services = []
        project_slug = project.lower().replace(' ', '-')

        if app_type in ['backend', 'fullstack']:
            dockerfile = prompt_dockerfile_location('backend', repo_path)
            service_name = prompt_service_name('backend', f"{project_slug}-backend")
            services.append({
                'type': 'backend',
                'name': service_name,
                'dockerfile': dockerfile
            })

        if app_type in ['frontend', 'fullstack']:
            dockerfile = prompt_dockerfile_location('frontend', repo_path)
            service_name = prompt_service_name('frontend', f"{project_slug}-frontend")
            services.append({
                'type': 'frontend',
                'name': service_name,
                'dockerfile': dockerfile
            })

        # Get GitHub repo URL
        github_repo_url = prompt_github_repo_url(client, project)

        # Get environments
        environments = prompt_environments()

        # Show summary
        show_cicd_summary(services, github_repo_url, environments)

        if confirm_cicd_setup():
            # Get platform configuration
            platform_project_id = get_platform_project_id()
            github_connection_id = get_github_connection_id()

            if not github_connection_id:
                console.print("[yellow]⚠ Skipping CI/CD setup (GitHub connection not configured)[/yellow]\n")
            else:
                # Generate CI/CD files in cicd/ folder (already created above)
                from solvigo.terraform.cicd_generator import generate_all_cicd_files

                cicd_success = generate_all_cicd_files(
                    client=client,
                    project=project,
                    platform_project_id=platform_project_id,
                    client_project_id=gcp_project_id,
                    github_connection_id=github_connection_id,
                    github_repo_url=github_repo_url,
                    services=services,
                    environments=environments,
                    terraform_dir=terraform_dir,
                    app_dir=cicd_dir  # Use cicd/ instead of app/
                )

                if cicd_success:
                    console.print("[green]✅ CI/CD configuration generated successfully![/green]\n")
                    console.print("[cyan]Generated files:[/cyan]")
                    console.print(f"  [dim]Terraform:[/dim] {terraform_dir}/")
                    console.print(f"  [dim]Build configs:[/dim] {cicd_dir}/")
                    console.print()

                    # Register project in Solvigo registry
                    try:
                        from solvigo.registry.client import RegistryClient

                        console.print("[cyan]Registering project in Solvigo registry...[/cyan]")

                        registry = RegistryClient()

                        # Prepare project data
                        client_slug = client.lower().replace(' ', '-')
                        project_slug = project.lower().replace(' ', '-')

                        # Register client (if new)
                        try:
                            registry.register_client({
                                'id': client_slug,
                                'name': client,
                                'subdomain': client_slug
                            })
                        except Exception as e:
                            # Client might already exist, that's ok
                            pass

                        # Prepare environment data
                        env_data = []
                        for env_name in environments:
                            env_data.append({
                                'project_id': f"{client_slug}-{project_slug}",
                                'name': env_name,
                                'database_instance': f"{project_slug}-db-{env_name}" if env_name != 'prod' else f"{project_slug}-db",
                                'database_type': 'postgresql',  # TODO: detect from selected resources
                                'auto_deploy': (env_name == 'staging'),
                                'requires_approval': (env_name == 'prod')
                            })

                        # Prepare service data
                        svc_data = []
                        for svc in services:
                            for env_name in environments:
                                svc_suffix = f"-{env_name}" if env_name != 'prod' else ""
                                svc_data.append({
                                    'project_id': f"{client_slug}-{project_slug}",
                                    'name': f"{svc['name']}{svc_suffix}",
                                    'type': svc['type'],
                                    'environment': env_name,
                                    'cloud_run_service': f"{svc['name']}{svc_suffix}",
                                    'cloud_run_region': 'europe-north1',
                                    'dockerfile_path': svc['dockerfile'],
                                    'cloudbuild_file': f"cicd/cloudbuild-{svc['type']}.yaml"
                                })

                        # Register project
                        registry.register_project({
                            'id': f"{client_slug}-{project_slug}",
                            'client_id': client_slug,
                            'name': project,
                            'subdomain': project_slug,
                            'full_domain': f"{project_slug}.{client_slug}.solvigo.ai",
                            'gcp_project_id': gcp_project_id,
                            'gcp_folder_id': client_folder_id,  # Track folder location
                            'github_repo': github_repo_url,
                            'terraform_state_bucket': f"{client_slug}-terraform-state",
                            'terraform_state_prefix': f"{project_slug}/prod",
                            'project_type': app_type,
                            'environments': env_data,
                            'services': svc_data
                        })

                        console.print("[green]✓ Registered in Solvigo registry[/green]\n")

                    except Exception as e:
                        console.print(f"[yellow]⚠ Could not register in registry: {e}[/yellow]")
                        console.print("[dim]Continuing without registry (not critical)...[/dim]\n")

                    console.print("[cyan]Next steps:[/cyan]")
                    console.print("  1. Review and commit the generated files")
                    console.print("  2. Push to GitHub to trigger first build")
                    console.print("  3. Monitor builds in Cloud Build console\n")

    # Ask if user wants to run import now
    console.print("\n" + "─" * 64 + "\n")

    run_now = confirm_action("Run Terraform import now?", default=True)

    if not run_now:
        console.print("\n[yellow]Configuration generated.[/yellow]")
        console.print(f"[dim]Run later with:[/dim]")
        console.print(f"  cd {terraform_dir}")
        console.print(f"  terraform init")
        console.print(f"  terraform plan")
        console.print(f"  terraform apply\n")
        return

    # Run Terraform import workflow
    from solvigo.terraform.runner import run_terraform_import_workflow

    success = run_terraform_import_workflow(terraform_dir, gcp_project_id)

    if success:
        console.print("\n[green bold]✅ Import completed successfully![/green bold]\n")
        console.print(f"[cyan]Your infrastructure is now managed by Terraform[/cyan]")
        console.print(f"[dim]Location: {terraform_dir}[/dim]\n")
    else:
        console.print("\n[yellow]Import workflow incomplete.[/yellow]")
        console.print(f"[dim]You can continue manually in: {terraform_dir}[/dim]\n")


def interactive_import_project():
    """
    Import existing GCP project interactively.
    """
    from solvigo.gcp.discovery import list_accessible_projects
    from solvigo.ui.prompts import select_option
    from rich.table import Table

    console.print("[bold]Let's import an existing GCP project![/bold]\n")

    # List all accessible projects
    console.print("[cyan]🔍 Listing your GCP projects...[/cyan]\n")

    projects = list_accessible_projects()

    if not projects:
        console.print("[red]✗ No GCP projects found or accessible[/red]")
        console.print("[yellow]Make sure you're authenticated: gcloud auth login[/yellow]\n")
        return

    # Filter to only ACTIVE projects
    active_projects = [p for p in projects if p.get('state') == 'ACTIVE']

    if not active_projects:
        console.print("[yellow]No active projects found.[/yellow]\n")
        return

    console.print(f"[green]✓ Found {len(active_projects)} accessible projects[/green]\n")

    # Let user choose search or browse
    gcp_project_id = select_project_interactive(active_projects)

    if not gcp_project_id:
        console.print("\n[yellow]No project selected.[/yellow]\n")
        return

    console.print(f"\n[green]Selected: {gcp_project_id}[/green]\n")

    import_existing_project(gcp_project_id)

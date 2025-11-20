"""
Add services to existing project - discovers GCP resources and generates Terraform
"""
from rich.console import Console
from rich.panel import Panel

from solvigo.gcp.discovery import ResourceDiscovery, verify_gcp_project_access
from solvigo.ui.prompts import select_resources, confirm_action

console = Console()


def add_services_to_existing_project(context: dict):
    """
    Add services to an existing project by discovering GCP resources.

    Args:
        context: Project context
    """
    from solvigo.gcp.discovery import list_accessible_projects
    from solvigo.commands.import_cmd import select_project_interactive

    client = context.get('client')
    project = context.get('project')

    # List all accessible projects
    console.print("[cyan]🔍 Listing your GCP projects...[/cyan]\n")

    projects = list_accessible_projects()

    if not projects:
        console.print("[red]✗ No GCP projects found or accessible[/red]")
        console.print("[yellow]Make sure you're authenticated: gcloud auth login[/yellow]\n")
        return

    # Filter to active projects
    active_projects = [p for p in projects if p.get('state') == 'ACTIVE']

    if not active_projects:
        console.print("[yellow]No active projects found.[/yellow]\n")
        return

    console.print(f"[green]✓ Found {len(active_projects)} accessible projects[/green]\n")

    # Use the same interactive selection as import workflow
    gcp_project_id = select_project_interactive(active_projects)

    if not gcp_project_id:
        console.print("\n[yellow]No project selected.[/yellow]\n")
        return

    console.print(f"\n[green]Selected: {gcp_project_id}[/green]")

    # Verify access
    console.print(f"\n[cyan]Verifying access to {gcp_project_id}...[/cyan]")

    if not verify_gcp_project_access(gcp_project_id):
        console.print(f"[red]✗ Cannot access project {gcp_project_id}[/red]")
        console.print("[yellow]Make sure you're authenticated: gcloud auth login[/yellow]")
        return

    console.print(f"[green]✓ Project accessible[/green]")

    # Ensure required APIs are enabled for discovery
    from solvigo.gcp.apis import ensure_discovery_apis

    api_result = ensure_discovery_apis(gcp_project_id)

    # Discover resources
    discovery = ResourceDiscovery(gcp_project_id)
    resources = discovery.discover_all()

    # Track which APIs were enabled (for Terraform generation later)
    resources['_enabled_apis'] = api_result['newly_enabled']
    resources['_all_apis'] = api_result['enabled_apis']

    # Let user select resources
    console.print("\n" + "─" * 64 + "\n")
    console.print("[bold]Select services to add to Terraform:[/bold]\n")

    selected = select_resources(resources, client=client, project=project)

    if not selected or all(len(v) == 0 for v in selected.values()):
        console.print("\n[yellow]No resources selected.[/yellow]")
        return

    # Show summary
    console.print("\n" + "─" * 64 + "\n")
    console.print("[bold]Summary of selected resources:[/bold]\n")

    total = 0
    for resource_type, items in selected.items():
        if items:
            console.print(f"  • {resource_type}: {len(items)} items")
            total += len(items)

    console.print(f"\n[cyan]Total: {total} resources[/cyan]\n")

    # Confirm
    if not confirm_action("Generate Terraform configuration?", default=True):
        console.print("\n[yellow]Cancelled.[/yellow]")
        return

    # ═══ Terraform Generation ═══
    from pathlib import Path

    # Detect terraform directory
    terraform_dir = context.get('terraform_path')

    if not terraform_dir or not terraform_dir.exists():
        # No terraform directory - treat like import workflow
        console.print("\n[yellow]No terraform directory found - creating from scratch[/yellow]\n")

        # Ask where to generate
        terraform_dir = context['path'] / 'terraform'

        if confirm_action(f"Create terraform directory at {terraform_dir}?", default=True):
            terraform_dir.mkdir(parents=True, exist_ok=True)

            # Generate complete configuration (like import)
            from solvigo.terraform.generator import generate_terraform_config

            if not generate_terraform_config(client, project, selected, terraform_dir):
                console.print("[red]✗ Failed to generate Terraform configuration[/red]\n")
                return
        else:
            console.print("\n[yellow]Cancelled.[/yellow]")
            return
    else:
        # Terraform directory exists - append to existing files
        console.print(f"\n[green]✓ Using existing terraform: {terraform_dir}[/green]\n")
        console.print("[cyan]📝 Adding new resources to existing configuration...[/cyan]\n")

        from solvigo.terraform.generator import (
            generate_cloud_run_tf,
            generate_cloud_sql_tf,
            generate_storage_tf,
            generate_secrets_tf,
            generate_service_accounts_tf,
            generate_imports_tf
        )

        # Append to existing files
        try:
            if selected.get('cloud_run'):
                generate_cloud_run_tf(client, project, selected['cloud_run'], terraform_dir, append=True)
                console.print("  ✓ Updated cloud-run.tf")

            if selected.get('cloud_sql'):
                generate_cloud_sql_tf(client, project, selected['cloud_sql'], terraform_dir, append=True)
                console.print("  ✓ Updated database-sql.tf")

            if selected.get('storage'):
                generate_storage_tf(client, project, selected['storage'], terraform_dir, append=True)
                console.print("  ✓ Updated storage.tf")

            if selected.get('secrets'):
                generate_secrets_tf(client, project, selected['secrets'], terraform_dir, append=True)
                console.print("  ✓ Updated secrets.tf")

            if selected.get('service_accounts'):
                generate_service_accounts_tf(client, project, selected['service_accounts'], terraform_dir, append=True)
                console.print("  ✓ Updated service-accounts.tf")

            # Always update imports.tf
            generate_imports_tf(client, project, selected, terraform_dir, append=True)
            console.print("  ✓ Updated imports.tf")

            console.print(f"\n[green]✓ Resources added to Terraform configuration[/green]\n")

        except Exception as e:
            console.print(f"\n[red]✗ Error updating Terraform: {e}[/red]\n")
            return

    # Ask if user wants to run terraform plan
    console.print("─" * 64 + "\n")

    if confirm_action("Run terraform plan to preview changes?", default=True):
        from solvigo.terraform.runner import run_terraform_plan

        console.print("\n[cyan]Running terraform plan...[/cyan]\n")

        if run_terraform_plan(terraform_dir):
            console.print("\n[green]✓ Plan complete[/green]\n")

            if confirm_action("Apply changes?", default=False):
                from solvigo.terraform.runner import run_terraform_apply

                if run_terraform_apply(terraform_dir):
                    console.print("\n[green]✅ Resources added successfully![/green]\n")
                else:
                    console.print("\n[yellow]Apply did not complete[/yellow]\n")
        else:
            console.print("\n[yellow]Plan failed[/yellow]\n")
    else:
        console.print("\n[cyan]Terraform files updated.[/cyan]")
        console.print(f"[dim]Run manually:[/dim]")
        console.print(f"  cd {terraform_dir}")
        console.print(f"  terraform plan")
        console.print(f"  terraform apply\n")

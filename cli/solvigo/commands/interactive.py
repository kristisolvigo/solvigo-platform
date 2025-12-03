"""
Interactive mode - main menu and flow control
"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from solvigo.ui.prompts import main_menu, confirm_action
from solvigo.commands.add_services import add_services_to_existing_project
from solvigo.commands.init import interactive_create_project
from solvigo.commands.import_cmd import interactive_import_project

console = Console()


def interactive_mode(context: dict):
    """
    Main interactive mode handler.

    Args:
        context: Project context from detect_project_context()
    """
    from pathlib import Path

    project_detected = context.get('exists', False)

    # Detect if terraform directory exists
    has_terraform = False
    if project_detected:
        git_root = context.get('git', {}).get('root') or context.get('path')
        if git_root:
            terraform_path = Path(git_root) / 'terraform'
            has_terraform = terraform_path.exists()

    if project_detected:
        # Show project info
        show_project_info(context)
    else:
        # Project not in registry - show helpful message
        if context.get('github_url'):
            console.print(Panel(
                f"[yellow]Project not found in registry[/yellow]\n\n"
                f"Repository: [cyan]{context['github_url']}[/cyan]\n\n"
                f"This repository is not registered in the Solvigo platform.\n"
                f"You can register it now to start managing it.",
                title="📝 Registration Required",
                border_style="yellow"
            ))
            console.print()

            # Offer to register
            if confirm_action("Would you like to register this project now?", default=True):
                handle_register_current_project(context)
                return  # Exit after registration to reload context
        else:
            console.print("[dim]No project detected in current directory.[/dim]\n")

    try:
        while True:
            # Show main menu with terraform status
            choice = main_menu(
                project_detected=project_detected,
                client=context.get('client'),
                project=context.get('project'),
                has_terraform=has_terraform
            )

            if not choice or '❌ Exit' in choice:
                console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
                break

            # Handle choice
            if '⚙️ Generate infrastructure' in choice:
                handle_generate_infrastructure(context)
                # Refresh terraform status after generation
                if project_detected:
                    git_root = context.get('git', {}).get('root') or context.get('path')
                    if git_root:
                        terraform_path = Path(git_root) / 'terraform'
                        has_terraform = terraform_path.exists()

            elif '🚀 Deploy' in choice:
                handle_deploy(context)

            elif '🗑️ Delete' in choice:
                handle_delete_project(context)

            elif '🆕 Create new project' in choice:
                handle_create_new_project()

            elif '📁 Choose' in choice:
                handle_choose_project()

            elif '📥 Import' in choice:
                handle_import_project()

            elif 'Setup new client' in choice:
                handle_setup_client()

    except KeyboardInterrupt:
        # Ctrl+C pressed - exit gracefully
        raise  # Re-raise to be caught by main.py


def show_project_info(context: dict):
    """Display detected project information."""
    from pathlib import Path

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("📂 Project", f"{context['client']}/{context['project']}")
    table.add_row("📍 Location", str(Path.cwd()))

    # Show GCP project if available
    if context.get('gcp_project_id'):
        table.add_row("☁️ GCP Project", context['gcp_project_id'])

    # Show domain if available
    if context.get('full_domain'):
        table.add_row("🌐 Domain", context['full_domain'])

    # Check for local terraform directory
    terraform_path = Path.cwd() / 'terraform'
    if terraform_path.exists():
        table.add_row("✓ Terraform", "[green]Found[/green]")
    else:
        table.add_row("⚠ Terraform", "[yellow]Not found[/yellow]")

    console.print(table)
    console.print()


def handle_add_services(context: dict):
    """Handle adding services to existing project."""
    console.print("\n[cyan]═══ Add Services to Terraform ═══[/cyan]\n")

    # Import and run the add services workflow
    add_services_to_existing_project(context)

    console.print()
    if confirm_action("Return to main menu?", default=True):
        return


def handle_deploy(context: dict):
    """Handle deployment."""
    from solvigo.commands.deploy import deploy_infrastructure
    from pathlib import Path

    console.print("\n[cyan]═══ Deploy Infrastructure ═══[/cyan]\n")

    # Set terraform_path in context
    git_root = context.get('git', {}).get('root') or context.get('path')
    if git_root:
        context['terraform_path'] = Path(git_root) / 'terraform'

    deploy_infrastructure(context)

    console.print()
    if confirm_action("Return to main menu?", default=True):
        return


def handle_generate_infrastructure(context: dict):
    """Handle infrastructure generation for registered project."""
    from solvigo.commands.init import generate_infrastructure_interactive
    from pathlib import Path

    console.print("\n[cyan]═══ Generate Infrastructure ═══[/cyan]\n")
    console.print("[dim]This will create Terraform and CI/CD configuration files.[/dim]\n")

    # Call the shared infrastructure generation function
    result = generate_infrastructure_interactive(context)

    if result.get('success'):
        # Update context to reflect terraform now exists
        git_root = context.get('git', {}).get('root') or context.get('path')
        if git_root:
            terraform_path = Path(git_root) / 'terraform'
            context['terraform_path'] = terraform_path

        console.print("\n[green bold]✨ Infrastructure generation complete![/green bold]\n")
        console.print("Next steps:")
        console.print("  1. Review generated files")
        console.print("  2. Commit and push to GitHub")
        console.print("  3. Run 'terraform init' and 'terraform apply'")
    else:
        console.print("\n[red]✗ Infrastructure generation failed[/red]")

    console.print()
    if confirm_action("Return to main menu?", default=True):
        return


def handle_status(context: dict):
    """Handle status viewing."""
    from solvigo.commands.status import show_status

    console.print("\n[cyan]═══ Project Status ═══[/cyan]\n")
    show_status(context)

    console.print()
    if confirm_action("Return to main menu?", default=True):
        return


def handle_configure(context: dict):
    """Handle configuration."""
    console.print("\n[cyan]═══ Configure Project ═══[/cyan]\n")
    console.print("[yellow]Configuration options coming soon...[/yellow]")

    console.print()
    if confirm_action("Return to main menu?", default=True):
        return


def handle_create_new_project():
    """Handle creating a new project."""
    console.print("\n[cyan]═══ Create New Project ═══[/cyan]\n")
    interactive_create_project()

    console.print()
    if confirm_action("Return to main menu?", default=True):
        return


def handle_choose_project():
    """Handle choosing an existing project."""
    from solvigo.utils.context import list_all_clients, find_client_projects
    from solvigo.ui.prompts import select_option
    import os

    console.print("\n[cyan]═══ Choose Existing Project ═══[/cyan]\n")

    # List all clients
    clients = list_all_clients()
    if not clients:
        console.print("[red]No clients found in the platform.[/red]")
        return

    # Let user select client
    selected_client = select_option(
        "Select client:",
        choices=clients
    )

    # List projects for that client
    projects = find_client_projects(selected_client)
    if not projects:
        console.print(f"[red]No projects found for {selected_client}.[/red]")
        return

    # Let user select project
    project_choices = [p['name'] for p in projects]
    selected_project = select_option(
        "Select project:",
        choices=project_choices
    )

    # Find the project directory
    project_dir = next(p['path'] for p in projects if p['name'] == selected_project)

    console.print(f"\n[green]✓[/green] Project: {selected_client}/{selected_project}")
    console.print(f"[dim]Location: {project_dir}[/dim]\n")

    if confirm_action(f"Change to {project_dir}?", default=True):
        console.print(f"\n[yellow]Please run:[/yellow]")
        console.print(f"  cd {project_dir}")
        console.print(f"  solvigo\n")


def handle_import_project():
    """Handle importing an existing GCP project."""
    console.print("\n[cyan]═══ Import Existing GCP Project ═══[/cyan]\n")
    interactive_import_project()

    console.print()
    if confirm_action("Return to main menu?", default=True):
        return


def handle_setup_client():
    """Handle setting up a new client."""
    from solvigo.ui.prompts import text_input

    console.print("\n[cyan]═══ Setup New Client ═══[/cyan]\n")

    client_name = text_input("Client name (lowercase, hyphens only):")

    console.print(f"\n[yellow]Setting up client: {client_name}[/yellow]")
    console.print("[dim]This feature is coming soon...[/dim]\n")


def handle_delete_project(context: dict):
    """Handle deleting project from registry."""
    console.print("\n[cyan]═══ Delete Project ═══[/cyan]\n")
    console.print(f"[red]⚠ This will remove {context['client']}/{context['project']} from the registry.[/red]")
    console.print("[dim]Note: This does NOT delete GCP resources or local files.[/dim]\n")

    if confirm_action("Are you sure you want to delete this project?", default=False):
        console.print("\n[yellow]Deleting project from registry...[/yellow]")

        from solvigo.admin.client import AdminClient
        registry = AdminClient(dev_mode=context.get('dev', False))

        # Use the actual project ID from the database (not constructed)
        # The project_data from the API has the correct ID
        project_id = context.get('project_data', {}).get('id') or context.get('project')

        console.print(f"[dim]Deleting project ID: {project_id}[/dim]\n")

        try:
            registry.delete_project(project_id)
            console.print(f"[green]✓ Project {project_id} deleted from registry.[/green]")
            console.print("[dim]You can now delete the local directory if desired.[/dim]\n")
            # Exit after deletion as context is invalid
            exit(0)
        except Exception as e:
            console.print(f"[red]✗ Failed to delete project: {e}[/red]\n")
    else:
        console.print("\n[dim]Cancelled.[/dim]\n")

    if confirm_action("Return to main menu?", default=True):
        return


def handle_register_current_project(context: dict):
    """
    Register the current repository as a new project.

    Walks through:
    1. Link GCP project
    2. Choose or create client
    3. Create project with subdomain and display name
    4. Save to database via API
    """
    from solvigo.ui.prompts import text_input, select_option
    from solvigo.admin.client import AdminClient

    console.print("\n[cyan]═══ Register New Project ═══[/cyan]\n")

    # Get GitHub URL
    github_url = context.get('github_url')
    if not github_url:
        console.print("[red]Error: No git remote URL found[/red]")
        return

    console.print(f"Repository: [cyan]{github_url}[/cyan]\n")

    # Step 1: Link GCP Project
    console.print("[bold]Step 1: Link GCP Project[/bold]\n")

    # List available GCP projects
    console.print("🔍 Listing your GCP projects...")
    try:
        from solvigo.gcp.discovery import list_accessible_projects
        gcp_projects = list_accessible_projects()

        if not gcp_projects:
            console.print("[red]No accessible GCP projects found[/red]")
            console.print("[dim]Make sure you're authenticated with gcloud[/dim]")
            return

        console.print(f"[green]✓ Found {len(gcp_projects)} accessible projects[/green]\n")

        # Let user choose or search
        search_query = text_input("Search for project (or press Enter to browse all):")

        if search_query:
            filtered = [p for p in gcp_projects if search_query.lower() in p['project_id'].lower() or search_query.lower() in p.get('name', '').lower()]
            if filtered:
                gcp_projects = filtered
            else:
                console.print(f"[yellow]No projects matching '{search_query}'[/yellow]")
                return

        # Show projects and let user select
        project_choices = [f"{p['project_id']} - {p.get('name', 'N/A')}" for p in gcp_projects[:20]]
        project_choices.append("❌ Cancel")

        selected = select_option("Select GCP project:", choices=project_choices)

        if "❌ Cancel" in selected:
            console.print("\n[dim]Cancelled.[/dim]\n")
            return

        gcp_project_id = selected.split(' - ')[0]
        console.print(f"\n[green]✓ Selected: {gcp_project_id}[/green]\n")

    except Exception as e:
        console.print(f"[red]Error listing GCP projects: {e}[/red]")
        # Fallback to manual entry
        gcp_project_id = text_input("Enter GCP Project ID manually:")

    # Step 2: Choose or Create Client
    console.print("[bold]Step 2: Choose or Create Client[/bold]\n")

    registry = AdminClient(dev_mode=context.get('dev', False))

    try:
        clients = registry.list_clients()
        console.print(f"[green]✓ Found {len(clients)} existing clients[/green]\n")
    except Exception as e:
        console.print(f"[yellow]⚠ Could not list clients: {e}[/yellow]")
        clients = []

    client_choices = [f"{c['name']} ({c['id']})" for c in clients]
    client_choices.append("➕ Create new client")
    client_choices.append("❌ Cancel")

    client_choice = select_option("Select client:", choices=client_choices)

    if "❌ Cancel" in client_choice:
        console.print("\n[dim]Cancelled.[/dim]\n")
        return

    if "➕ Create new client" in client_choice:
        # Create new client
        console.print("\n[cyan]Creating new client...[/cyan]\n")

        client_display_name = text_input("Client display name (e.g., 'ACME Corporation'):")
        client_subdomain = text_input("Client subdomain (lowercase, no spaces, e.g., 'acme-corp'):")
        client_id = client_subdomain  # Use subdomain as ID

        # Register client
        try:
            client_data = {
                'id': client_id,
                'name': client_display_name,
                'subdomain': client_subdomain
            }
            registry.register_client(client_data)
            console.print(f"\n[green]✓ Client '{client_display_name}' created[/green]\n")
        except Exception as e:
            console.print(f"[red]✗ Failed to create client: {e}[/red]")
            return
    else:
        # Use existing client - fetch full details to get subdomain
        client_id = client_choice.split('(')[1].rstrip(')')
        try:
            client_details = registry.get_client(client_id)
            client_subdomain = client_details['subdomain']
        except Exception as e:
            console.print(f"[red]✗ Failed to fetch client details: {e}[/red]")
            return

    # Step 3: Create Project
    console.print("[bold]Step 3: Create Project[/bold]\n")

    project_display_name = text_input("Project display name (e.g., 'Customer Portal'):")
    project_subdomain = text_input("Project subdomain (lowercase, no spaces, e.g., 'portal'):")

    # Generate project ID: client_subdomain-project_subdomain (shorter format)
    project_id = f"{client_subdomain}-{project_subdomain}"

    # Full domain - use client_subdomain, not client_id
    full_domain = f"{project_subdomain}.{client_subdomain}.solvigo.ai"

    # Step 4: Save to Database
    console.print(f"\n[yellow]Registering project in database...[/yellow]\n")

    try:
        project_data = {
            'id': project_id,
            'client_id': client_id,
            'name': project_display_name,
            'subdomain': project_subdomain,
            'full_domain': full_domain,
            'gcp_project_id': gcp_project_id,
            'github_repo': github_url,
            'project_type': 'fullstack',  # Default
            'status': 'active'
        }

        registry.register_project(project_data)

        console.print(Panel(
            f"[green]✓ Project registered successfully![/green]\n\n"
            f"Project ID: [cyan]{project_id}[/cyan]\n"
            f"Client: [cyan]{client_id}[/cyan]\n"
            f"GCP Project: [cyan]{gcp_project_id}[/cyan]\n"
            f"Domain: [cyan]{full_domain}[/cyan]\n"
            f"Repository: [cyan]{github_url}[/cyan]\n\n"
            f"[dim]You can now use the Solvigo CLI to manage this project.[/dim]",
            title="🎉 Registration Complete",
            border_style="green"
        ))
        console.print()

        console.print("[yellow]Tip:[/yellow] Run [cyan]solvigo --dev[/cyan] again to reload the project context.\n")

    except Exception as e:
        console.print(f"[red]✗ Failed to register project: {e}[/red]")
        console.print(f"[dim]Details: {str(e)}[/dim]\n")

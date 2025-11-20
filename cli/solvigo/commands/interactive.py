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
    project_detected = context.get('exists', False)

    if project_detected:
        # Show project info
        show_project_info(context)
    else:
        console.print("[dim]No project detected in current directory.[/dim]\n")

    try:
        while True:
            # Show main menu
            choice = main_menu(
                project_detected=project_detected,
                client=context.get('client'),
                project=context.get('project')
            )

            if not choice or '❌ Exit' in choice:
                console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
                break

            # Handle choice
            if '✨ Add services' in choice:
                handle_add_services(context)

            elif '🚀 Deploy' in choice:
                handle_deploy(context)

            elif '📊 View project status' in choice:
                handle_status(context)

            elif '🔧 Configure' in choice:
                handle_configure(context)

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
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("📂 Project", f"{context['client']}/{context['project']}")
    table.add_row("📍 Location", str(context['path']))

    if context.get('has_terraform'):
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

    console.print("\n[cyan]═══ Deploy Infrastructure ═══[/cyan]\n")
    deploy_infrastructure(context)

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

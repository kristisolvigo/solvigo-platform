"""
Initialize new project - create infrastructure and scaffold code
"""
from rich.console import Console

console = Console()


def create_project(client: str, project: str, environment: str, stack: str,
                  database: str, new_client: bool, dry_run: bool):
    """
    Create a new project (non-interactive version).

    Args:
        client: Client name
        project: Project name
        environment: Environment (dev/prod/staging)
        stack: Application stack type
        database: Database type
        new_client: Whether this is a new client
        dry_run: Whether to do dry run
    """
    console.print(f"\n[cyan]Creating project: {client}/{project}[/cyan]")
    console.print(f"[dim]Environment: {environment}[/dim]")
    console.print(f"[dim]Stack: {stack}[/dim]")
    console.print(f"[dim]Database: {database}[/dim]\n")

    console.print("[yellow]⚠ Project creation not yet implemented[/yellow]")
    console.print("[dim]This will:[/dim]")
    console.print("[dim]  1. Create GCP project(s)[/dim]")
    console.print("[dim]  2. Generate directory structure[/dim]")
    console.print("[dim]  3. Generate Terraform configs[/dim]")
    console.print("[dim]  4. Scaffold application code[/dim]")
    console.print("[dim]  5. Deploy infrastructure[/dim]\n")


def interactive_create_project():
    """
    Create a new project interactively.
    """
    from solvigo.ui.prompts import text_input, select_option, confirm_action

    console.print("[bold]Let's create a new project![/bold]\n")

    # Get client name
    client = text_input("Client name (lowercase, hyphens only):")

    # Check if client exists
    from solvigo.utils.context import list_all_clients

    existing_clients = list_all_clients()
    new_client = client not in existing_clients

    if new_client:
        console.print(f"[yellow]→ This will be a new client[/yellow]")
    else:
        console.print(f"[green]✓ Client exists[/green]")

    # Get project name
    project = text_input("Project name (lowercase, hyphens only):")

    # Get environment
    env_choice = select_option(
        "Environment setup:",
        choices=[
            "Development only",
            "Production only",
            "Both dev and prod (recommended)",
            "Dev, Staging, and Production"
        ]
    )

    # Get stack type
    stack = select_option(
        "What type of application?",
        choices=[
            "Fullstack (Frontend + Backend)",
            "Frontend only",
            "Backend only",
            "API only"
        ]
    )

    # Get database
    database = select_option(
        "Database:",
        choices=[
            "PostgreSQL (Cloud SQL)",
            "MySQL (Cloud SQL)",
            "Firestore",
            "Both SQL + Firestore",
            "None"
        ]
    )

    # Confirm
    console.print("\n" + "─" * 64)
    console.print("[bold]Summary:[/bold]\n")
    console.print(f"  Client:      {client}")
    console.print(f"  Project:     {project}")
    console.print(f"  Environment: {env_choice}")
    console.print(f"  Stack:       {stack}")
    console.print(f"  Database:    {database}")
    console.print("─" * 64 + "\n")

    if confirm_action("Create this project?", default=True):
        console.print("\n[cyan]🚀 Creating project...[/cyan]\n")
        console.print("[yellow]⚠ Project creation not yet implemented[/yellow]")
        console.print("[dim]When implemented, this will also include CI/CD setup:[/dim]")
        console.print("[dim]  - Cloud Build triggers for dev/staging/prod[/dim]")
        console.print("[dim]  - Artifact Registry for Docker images[/dim]")
        console.print("[dim]  - GitHub repository integration[/dim]")
        console.print("[dim]  - Automated deployment pipeline[/dim]\n")

        # TODO: When init is fully implemented, add CI/CD prompts here
        # Similar to import_cmd.py lines 248-331
    else:
        console.print("\n[yellow]Cancelled.[/yellow]\n")

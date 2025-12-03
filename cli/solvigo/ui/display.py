"""Display components for project information"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from solvigo.domain.entities import ProjectInfo, GitRepoInfo

console = Console()


def display_project_info(project: ProjectInfo, git_info: GitRepoInfo):
    """
    Display full project details from database.

    Shows: name, client, GCP project ID, environments, services,
           last deployment, domain, and git status
    """
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Project", f"[bold]{project.name}[/bold]")
    table.add_row("Client", project.client_id)
    table.add_row("GCP Project", project.gcp_project_id or "[dim]Not set[/dim]")
    table.add_row("Domain", project.full_domain or "[dim]Not set[/dim]")

    # Environments
    env_names = ", ".join([e.name for e in project.environments]) or "[dim]None[/dim]"
    table.add_row("Environments", env_names)

    # Services
    if project.services:
        svc_info = ", ".join([f"{s.name} ({s.type})" for s in project.services])
        table.add_row("Services", svc_info)
    else:
        table.add_row("Services", "[dim]None configured[/dim]")

    # Last deployment
    if project.last_deployed_at:
        table.add_row("Last Deploy", str(project.last_deployed_at))

    # Git info
    table.add_row("Branch", f"[cyan]{git_info.branch}[/cyan]")
    status = "[yellow]Uncommitted changes[/yellow]" if git_info.has_changes else "[green]Clean[/green]"
    table.add_row("Status", status)

    console.print()
    console.print(Panel(table, title="[bold cyan]Project Details[/bold cyan]", border_style="cyan"))
    console.print()


def display_billing_required(project: ProjectInfo):
    """Display billing linking required message"""
    console.print()
    console.print(Panel(
        f"[yellow]Billing Required[/yellow]\n\n"
        f"GCP project [bold]{project.gcp_project_id}[/bold] needs billing linked.\n\n"
        "[dim]Steps:[/dim]\n"
        "  1. Go to Google Cloud Console\n"
        "  2. Navigate to Billing\n"
        "  3. Link a billing account\n"
        "  4. Re-run [cyan]solvigo[/cyan] to continue",
        title="[yellow]Action Required[/yellow]",
        border_style="yellow"
    ))
    console.print()


def display_project_not_found(git_info: GitRepoInfo):
    """Display message when project not found in database"""
    console.print()
    console.print(Panel(
        "[dim]This repository is not registered as a Solvigo project.[/dim]\n\n"
        f"Repository: [cyan]{git_info.remote or 'No remote configured'}[/cyan]",
        title="[cyan]New Repository[/cyan]",
        border_style="cyan"
    ))
    console.print()


def display_api_error(error_message: str):
    """Display API connection error"""
    console.print(f"[yellow]Could not connect to Solvigo API: {error_message}[/yellow]")
    console.print("[dim]Some features may be limited.[/dim]\n")

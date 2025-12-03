"""
Show project status
"""
from rich.console import Console
from rich.table import Table

console = Console()


def show_status(context: dict):
    """
    Show status of a project.

    Args:
        context: Project context
    """
    client = context.get('client')
    project = context.get('project')

    console.print(f"[bold]Status for {client}/{project}[/bold]\n")

    # Create status table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Details")

    # Check terraform locally
    from pathlib import Path
    terraform_path = Path.cwd() / 'terraform'
    if terraform_path.exists():
        table.add_row("Terraform", "[green]✓ Found[/green]", str(terraform_path))
    else:
        table.add_row("Terraform", "[red]✗ Not found[/red]", "-")

    # TODO: Add more status checks
    # - GCP project exists
    # - Cloud Run services deployed
    # - Database status
    # - Load balancer registration
    # - DNS records

    console.print(table)
    console.print()

    console.print("[yellow]⚠ Full status checking not yet implemented[/yellow]\n")

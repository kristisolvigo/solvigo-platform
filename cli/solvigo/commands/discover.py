"""
Discover resources in a GCP project
"""
from rich.console import Console
from rich.table import Table

from solvigo.gcp.discovery import ResourceDiscovery, verify_gcp_project_access

console = Console()


def discover_resources(gcp_project_id: str):
    """
    Discover and display resources in a GCP project.

    Args:
        gcp_project_id: GCP project ID
    """
    console.print(f"\n[bold cyan]Discovering resources in: {gcp_project_id}[/bold cyan]\n")

    # Verify access
    if not verify_gcp_project_access(gcp_project_id):
        console.print(f"[red]✗ Cannot access project {gcp_project_id}[/red]")
        console.print("[yellow]Make sure you're authenticated: gcloud auth login[/yellow]")
        return

    # Discover
    discovery = ResourceDiscovery(gcp_project_id)
    resources = discovery.discover_all()

    # Display detailed results
    console.print("\n" + "═" * 64 + "\n")

    # Cloud Run
    if resources.get('cloud_run'):
        console.print("[bold cyan]Cloud Run Services:[/bold cyan]\n")
        table = Table()
        table.add_column("Name")
        table.add_column("Region")
        table.add_column("Type")
        table.add_column("URL")

        for service in resources['cloud_run']:
            table.add_row(
                service['name'],
                service.get('region', 'unknown'),
                service.get('type', 'unknown'),
                service.get('url', '-')
            )

        console.print(table)
        console.print()

    # Cloud SQL
    if resources.get('cloud_sql'):
        console.print("[bold cyan]Cloud SQL Databases:[/bold cyan]\n")
        table = Table()
        table.add_column("Name")
        table.add_column("Version")
        table.add_column("Tier")
        table.add_column("Region")

        for db in resources['cloud_sql']:
            table.add_row(
                db['name'],
                db.get('database_version', 'unknown'),
                db.get('tier', 'unknown'),
                db.get('region', 'unknown')
            )

        console.print(table)
        console.print()

    # Storage
    if resources.get('storage'):
        console.print(f"[bold cyan]Storage Buckets:[/bold cyan] {len(resources['storage'])} found\n")

    # Secrets
    if resources.get('secrets'):
        console.print(f"[bold cyan]Secrets:[/bold cyan] {len(resources['secrets'])} found\n")

    # Service Accounts
    if resources.get('service_accounts'):
        console.print(f"[bold cyan]Service Accounts:[/bold cyan] {len(resources['service_accounts'])} found\n")

    # APIs
    if resources.get('apis'):
        console.print("[bold cyan]Enabled APIs:[/bold cyan]\n")
        for api in resources['apis']:
            console.print(f"  • {api['title']}")
        console.print()

    console.print("═" * 64 + "\n")

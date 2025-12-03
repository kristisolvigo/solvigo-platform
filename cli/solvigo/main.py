"""
Main entry point for the Solvigo CLI
"""
import sys
import click
from rich.console import Console
from rich.panel import Panel

from solvigo.commands.interactive import interactive_mode
from solvigo.utils.context import detect_project_context
from solvigo import __version__

console = Console()


@click.group(invoke_without_command=True)
@click.version_option(version=__version__)
@click.option('--dev', is_flag=True, help='Run in development mode (connect to local Admin API)')
@click.pass_context
def cli(ctx, dev):
    """
    Solvigo CLI - Interactive tool for managing client projects on GCP

    Run without arguments for interactive mode.
    """
    ctx.ensure_object(dict)
    ctx.obj['dev'] = dev

    if ctx.invoked_subcommand is None:
        # No subcommand provided - run interactive mode
        run_interactive(ctx)


def run_interactive(ctx=None):
    """Run the interactive CLI mode"""
    try:
        # Welcome banner
        console.print()
        console.print(Panel.fit(
            f"🚀 [bold cyan]Welcome to Solvigo CLI[/bold cyan] [dim]v{__version__}[/dim]",
            border_style="cyan"
        ))
        console.print()

        # Check for git repository (required for CLI operations)
        from solvigo.utils.git import verify_git_repo_or_exit
        git_info = verify_git_repo_or_exit()

        # Authenticate user (optional - gracefully degrade if fails)
        from solvigo.services.cli_auth_service import CLIAuthService

        try:
            user_email = CLIAuthService.ensure_authenticated()
            console.print(f"[dim]✓ Authenticated as: {user_email}[/dim]\n")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not authenticate: {e}[/yellow]")
            console.print("[dim]Some features may be limited.[/dim]\n")
            user_email = None

        # Detect context (pass dev flag to query correct API)
        dev_mode = ctx.obj.get('dev', False) if ctx and ctx.obj else False
        context = detect_project_context(dev_mode=dev_mode)
        context['git'] = git_info  # Add git info to context
        context['user_email'] = user_email
        context['dev'] = dev_mode

        # Run interactive mode
        interactive_mode(context)

    except KeyboardInterrupt:
        # Handle Ctrl+C - exit gracefully
        console.print("\n\n[cyan]Goodbye! 👋[/cyan]\n")
        sys.exit(0)


@cli.command()
@click.argument('client')
@click.argument('project')
@click.option('--env', default='prod', help='Environment (dev/staging/prod)')
@click.option('--stack', type=click.Choice(['frontend', 'backend', 'fullstack']),
              default='fullstack', help='Application stack')
@click.option('--database', type=click.Choice(['none', 'firestore', 'postgres']),
              default='none', help='Database type')
@click.option('--new-client', is_flag=True, help='This is a new client')
@click.option('--dry-run', is_flag=True, help='Generate configuration without deploying')
def init(client, project, env, stack, database, new_client, dry_run):
    """
    Create a new client project with infrastructure setup

    Example:
        solvigo init acme-corp dashboard --env prod --stack fullstack
    """
    from solvigo.commands.init import create_project

    create_project(
        client=client,
        project=project,
        environment=env,
        stack=stack,
        database=database,
        new_client=new_client,
        dry_run=dry_run
    )


@cli.command()
@click.argument('gcp_project_id')
@click.option('--client', help='Client name')
@click.option('--project', help='Project name')
@click.option('--dry-run', is_flag=True, help='Preview import without applying')
def import_project(gcp_project_id, client, project, dry_run):
    """
    Import existing GCP project into Solvigo platform

    Example:
        solvigo import existing-project-123 --client acme-corp --project legacy-app
    """
    from solvigo.commands.import_cmd import import_existing_project

    import_existing_project(
        gcp_project_id=gcp_project_id,
        client=client,
        project=project,
        dry_run=dry_run
    )


@cli.command()
@click.argument('gcp_project_id')
def discover(gcp_project_id):
    """
    Discover resources in a GCP project

    Example:
        solvigo discover acme-corp-app1-prod
    """
    from solvigo.commands.discover import discover_resources

    discover_resources(gcp_project_id)


@cli.command()
@click.option('--env', help='Specific environment to deploy')
def deploy(env):
    """
    Deploy infrastructure for current project

    Example:
        solvigo deploy --env prod
    """
    from solvigo.commands.deploy import deploy_infrastructure
    from pathlib import Path

    context = detect_project_context()
    if not context['exists']:
        console.print("[red]Error:[/red] No project detected in current directory")
        console.print("Run [cyan]solvigo init[/cyan] to create a new project")
        return

    # Set terraform_path in context (use current directory)
    context['terraform_path'] = Path.cwd() / 'terraform'

    deploy_infrastructure(context, environment=env)


@cli.command()
def status():
    """
    Show status of current project

    Example:
        solvigo status
    """
    from solvigo.commands.status import show_status

    context = detect_project_context()
    if not context['exists']:
        console.print("[red]Error:[/red] No project detected in current directory")
        return

    show_status(context)


if __name__ == '__main__':
    cli()

"""
CI/CD setup prompts for Cloud Build integration
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
import questionary
from questionary import Choice

console = Console()


def prompt_cicd_setup() -> bool:
    """
    Ask user if they want to set up CI/CD pipeline.

    Returns:
        True if user wants CI/CD, False otherwise
    """
    console.print("\n[cyan]═══ CI/CD Setup ═══[/cyan]\n")
    console.print("Set up automated deployments with Cloud Build?")
    console.print("[dim]This will create build triggers for dev/staging/prod environments[/dim]\n")

    result = questionary.confirm(
        "Setup CI/CD pipeline?",
        default=True
    ).ask()

    return result if result is not None else False


def prompt_application_type() -> str:
    """
    Ask user what type of application this is.

    Returns:
        'backend', 'frontend', or 'fullstack'
    """
    console.print("\n[cyan]What type of application is this?[/cyan]\n")

    choices = [
        Choice("🔧 Backend (API, services, etc.)", value="backend"),
        Choice("🎨 Frontend (Web UI, React, etc.)", value="frontend"),
        Choice("🌐 Fullstack (Both backend and frontend)", value="fullstack"),
    ]

    result = questionary.select(
        "Application type:",
        choices=choices
    ).ask()

    return result if result else "backend"


def scan_directory(path: Path) -> dict:
    """
    Scan directory and categorize items.

    Args:
        path: Directory to scan

    Returns:
        dict with 'directories' and 'dockerfiles' lists
    """
    items = {
        'directories': [],
        'dockerfiles': [],
        'other_files': []
    }

    # Skip these directories
    skip_dirs = {
        'node_modules', '__pycache__', 'venv', 'env', '.git',
        '.terraform', 'dist', 'build', '.next', 'target'
    }

    try:
        for item in sorted(path.iterdir()):
            # Skip hidden files and excluded directories
            if item.name.startswith('.') or item.name in skip_dirs:
                continue

            if item.is_dir():
                # Check if directory contains any Dockerfile
                has_dockerfile = any([
                    (item / 'Dockerfile').exists(),
                    (item / 'Dockerfile.dev').exists(),
                    (item / 'Dockerfile.prod').exists(),
                ])
                items['directories'].append({
                    'name': item.name,
                    'has_dockerfile': has_dockerfile
                })

            elif 'Dockerfile' in item.name or item.suffix == '.dockerfile':
                items['dockerfiles'].append(item.name)
            else:
                items['other_files'].append(item.name)

    except PermissionError:
        pass

    return items


def browse_for_dockerfile(
    service_type: str,
    base_path: Path,
    current_path: Path
) -> str:
    """
    Recursive interactive directory browser for Dockerfile selection.

    Args:
        service_type: 'backend' or 'frontend'
        base_path: Base directory (repo root)
        current_path: Current relative path from base

    Returns:
        Path to selected Dockerfile
    """
    full_path = base_path / current_path

    # Scan current directory
    items = scan_directory(full_path)

    # Build choices
    choices = []

    # Show current path
    path_display = str(current_path) if str(current_path) != '.' else './ (repository root)'
    console.print(f"\n[cyan]📂 Browse: {path_display}[/cyan]")
    console.print(f"[dim]Select Dockerfile for {service_type}[/dim]\n")

    # Add parent directory option if not at root
    if current_path != Path('.'):
        choices.append(Choice("📁 ../  [Go up one level]", value="__parent__"))
        if choices:
            choices.append(Choice("─" * 50, value=None, disabled=True))

    # Add Dockerfiles in current directory (priority)
    for dockerfile in items['dockerfiles']:
        rel_path = current_path / dockerfile if str(current_path) != '.' else Path(dockerfile)
        choices.append(Choice(f"🐳 {dockerfile}  [Select this file]", value=str(rel_path)))

    # Add separator if we have files and directories
    if items['dockerfiles'] and items['directories']:
        choices.append(Choice("─" * 50, value=None, disabled=True))

    # Add directories (highlight if contains Dockerfile)
    for dir_item in items['directories'][:20]:  # Limit to 20 directories
        has_dockerfile = dir_item['has_dockerfile']
        icon = "📦" if has_dockerfile else "📁"
        suffix = "  [Contains Dockerfile ✓]" if has_dockerfile else "  [Navigate]"
        label = f"{icon} {dir_item['name']}/{suffix}"
        choices.append(Choice(label, value=f"__dir__{dir_item['name']}"))

    # Add custom path option
    if choices:
        choices.append(Choice("─" * 50, value=None, disabled=True))
    choices.append(Choice("⌨️  Enter custom path...", value="__custom__"))

    # Prompt
    result = questionary.select(
        f"Select Dockerfile location:",
        choices=choices
    ).ask()

    # Handle selection
    if result == "__parent__":
        # Go up one level
        parent_path = current_path.parent if current_path != Path('.') else Path('.')
        return browse_for_dockerfile(service_type, base_path, parent_path)

    elif result and result.startswith("__dir__"):
        # Navigate into directory
        dir_name = result.replace("__dir__", "")
        return browse_for_dockerfile(service_type, base_path, current_path / dir_name)

    elif result == "__custom__":
        # Custom path
        console.print()
        custom = questionary.text(
            "Enter Dockerfile path (relative to repository root):",
            default=f"{service_type}/Dockerfile"
        ).ask()
        return custom if custom else f"{service_type}/Dockerfile"

    else:
        # File selected
        return result if result else f"{service_type}/Dockerfile"


def prompt_dockerfile_location(service_type: str, base_path: Path = None) -> str:
    """
    Interactive file browser for selecting Dockerfile location.

    Args:
        service_type: 'backend' or 'frontend'
        base_path: Base directory to search (defaults to current directory)

    Returns:
        Path to Dockerfile (e.g., 'backend/Dockerfile', './Dockerfile')
    """
    if base_path is None:
        base_path = Path.cwd()

    console.print(f"\n[cyan]═══ Select Dockerfile for {service_type} ═══[/cyan]")

    # Start browsing from root
    return browse_for_dockerfile(service_type, base_path, Path('.'))


def prompt_repository_location(client: str, project: str) -> Path:
    """
    Ask user where their application code repository is located.

    This is the local clone of the GitHub repository that contains
    the application code and Dockerfiles.

    Args:
        client: Client name
        project: Project name

    Returns:
        Path to repository directory
    """
    console.print("\n[cyan]═══ Application Code Location ═══[/cyan]\n")
    console.print("Where is your application code located?")
    console.print("[dim]This should be your local GitHub repository with Dockerfiles.[/dim]\n")

    # Try to guess common locations
    home = Path.home()
    client_slug = client.lower().replace(' ', '-')
    project_slug = project.lower().replace(' ', '-')

    guesses = [
        Path.cwd(),  # Current directory
        home / "repos" / f"{client_slug}-{project_slug}",
        home / "Desktop" / f"{client_slug}-{project_slug}",
        home / "projects" / f"{client_slug}-{project_slug}",
        home / "Documents" / f"{client_slug}-{project_slug}",
    ]

    # Find first existing directory with .git
    default = str(Path.cwd())
    for guess in guesses:
        if guess.exists() and (guess / '.git').exists():
            default = str(guess)
            console.print(f"[green]✓ Found repository: {guess}[/green]\n")
            break

    result = questionary.text(
        "Application code directory path:",
        default=default
    ).ask()

    repo_path = Path(result) if result else Path.cwd()

    # Validate it exists
    if not repo_path.exists():
        console.print(f"[yellow]⚠ Directory not found: {repo_path}[/yellow]")
        console.print("[dim]Please enter a valid path to your code repository.[/dim]\n")
        return prompt_repository_location(client, project)

    return repo_path


def prompt_service_name(service_type: str, default: str) -> str:
    """
    Prompt for Cloud Run service name.

    Args:
        service_type: 'backend' or 'frontend'
        default: Default service name

    Returns:
        Service name
    """
    console.print(f"\n[cyan]Cloud Run service name for {service_type}:[/cyan]")
    console.print(f"[dim]This will be deployed to Cloud Run[/dim]\n")

    result = questionary.text(
        f"{service_type.capitalize()} service name:",
        default=default
    ).ask()

    return result if result else default


def prompt_github_repo_url(client: str, project: str) -> str:
    """
    Prompt for GitHub repository URL.

    Args:
        client: Client name
        project: Project name

    Returns:
        GitHub repository URL
    """
    console.print("\n[cyan]GitHub Repository:[/cyan]")
    console.print("[dim]This should be the HTTPS URL of your GitHub repository[/dim]\n")

    # Generate a sensible default
    client_slug = client.lower().replace(' ', '-')
    project_slug = project.lower().replace(' ', '-')
    default_url = f"https://github.com/solvigo/{client_slug}-{project_slug}.git"

    result = questionary.text(
        "GitHub repository URL:",
        default=default_url
    ).ask()

    return result if result else default_url


def prompt_environments() -> List[str]:
    """
    Prompt user to select which environments to set up.

    Returns:
        List of environments (e.g., ['staging', 'prod'])
    """
    console.print("\n[cyan]Which environments do you want to set up?[/cyan]\n")
    console.print("[dim]Note: Local development uses docker-compose (not cloud deployment)[/dim]\n")

    choices = [
        Choice("Staging (auto-deploy on push to main)", value="staging", checked=True),
        Choice("Prod (manual approval, tag-based)", value="prod", checked=True),
    ]

    result = questionary.checkbox(
        "Select environments:",
        choices=choices
    ).ask()

    return result if result else ["staging", "prod"]


def show_cicd_summary(services: List[Dict], github_repo_url: str, environments: List[str]):
    """
    Display a summary of CI/CD setup.

    Args:
        services: List of service configurations
        github_repo_url: GitHub repository URL
        environments: List of environments
    """
    console.print("\n[cyan]═══ CI/CD Setup Summary ═══[/cyan]\n")

    # Services table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Service Type")
    table.add_column("Service Name")
    table.add_column("Dockerfile")

    for service in services:
        table.add_row(
            service['type'].capitalize(),
            service['name'],
            service['dockerfile']
        )

    console.print(table)
    console.print()

    # Repository and environments
    console.print(f"[cyan]Repository:[/cyan] {github_repo_url}")
    console.print(f"[cyan]Environments:[/cyan] {', '.join(environments)}")
    console.print()


def confirm_cicd_setup() -> bool:
    """
    Ask user to confirm CI/CD setup.

    Returns:
        True if confirmed, False otherwise
    """
    result = questionary.confirm(
        "Proceed with CI/CD setup?",
        default=True
    ).ask()

    return result if result is not None else False


def get_platform_project_id() -> str:
    """
    Get platform project ID from environment or config.

    Returns:
        Platform project ID
    """
    # Try environment variable first
    platform_project = os.getenv('SOLVIGO_PLATFORM_PROJECT')
    if platform_project:
        return platform_project

    # Try reading from .solvigo_config
    config_file = Path.cwd() / '.solvigo_config'
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                for line in f:
                    if line.startswith('export SOLVIGO_PLATFORM_PROJECT='):
                        value = line.split('=')[1].strip().strip('"')
                        return value
        except Exception:
            pass

    # Default
    return "solvigo-platform-prod"


def get_github_connection_id(dev_mode: bool = False) -> Optional[str]:
    """
    Get GitHub connection ID from Admin API.

    Args:
        dev_mode: Whether running in dev mode

    Returns:
        GitHub connection resource name or None
    """
    from solvigo.admin.client import AdminClient

    try:
        admin_client = AdminClient(dev_mode=dev_mode)

        # Call Admin API to get platform configuration
        platform_config = admin_client.get_platform_config()

        # Extract GitHub connection from config
        github_connection = platform_config.get('github_connection')

        if github_connection:
            return github_connection
        else:
            console.print("\n[yellow]⚠ GitHub connection not configured in platform[/yellow]")
            console.print("[dim]Contact platform admin to set up GitHub connection[/dim]\n")
            return None

    except Exception as e:
        console.print(f"\n[yellow]⚠ Failed to fetch platform config: {e}[/yellow]")
        console.print("[dim]Make sure Admin API is accessible[/dim]\n")
        return None

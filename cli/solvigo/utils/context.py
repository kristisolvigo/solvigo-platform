"""
Context detection - determines if CLI is running from a project directory
"""
import os
from pathlib import Path
import re
from typing import Dict, Optional


def detect_project_context() -> Dict[str, any]:
    """
    Detect if running from within a Solvigo project directory.

    Returns:
        dict: Context information with keys:
            - exists (bool): Whether a project was detected
            - client (str): Client name
            - project (str): Project name
            - path (Path): Project directory path
            - terraform_path (Path): Path to terraform directory
            - has_terraform (bool): Whether terraform directory exists
    """
    cwd = Path.cwd()

    # Check if we're in the clients/ structure
    # Pattern: clients/{client}/{project}/
    if 'clients' in cwd.parts:
        client_idx = cwd.parts.index('clients')

        # We need at least clients/{client}/{project}
        if len(cwd.parts) > client_idx + 2:
            client = cwd.parts[client_idx + 1]
            project = cwd.parts[client_idx + 2]

            # Find the project root (clients/{client}/{project}/)
            project_root = Path('/'.join(cwd.parts[:client_idx + 3]))
            terraform_path = project_root / 'terraform'

            return {
                'exists': True,
                'client': client,
                'project': project,
                'path': project_root,
                'terraform_path': terraform_path,
                'has_terraform': terraform_path.exists(),
                'current_dir': cwd
            }

    # Check if terraform/ exists in current directory
    # This handles the case where we're AT clients/{client}/{project}/
    terraform_path = cwd / 'terraform'
    if terraform_path.exists():
        # Try to infer from directory structure
        if 'clients' in cwd.parts:
            client_idx = cwd.parts.index('clients')
            if len(cwd.parts) > client_idx + 2:
                return {
                    'exists': True,
                    'client': cwd.parts[client_idx + 1],
                    'project': cwd.parts[client_idx + 2],
                    'path': cwd,
                    'terraform_path': terraform_path,
                    'has_terraform': True,
                    'current_dir': cwd
                }

        # Try to parse from terraform backend.tf
        backend_config = parse_backend_config(terraform_path / 'backend.tf')
        if backend_config:
            return {
                'exists': True,
                'client': backend_config.get('client'),
                'project': backend_config.get('project'),
                'path': cwd,
                'terraform_path': terraform_path,
                'has_terraform': True,
                'current_dir': cwd,
                'inferred': True
            }

    # No project detected
    return {
        'exists': False,
        'current_dir': cwd
    }


def parse_backend_config(backend_file: Path) -> Optional[Dict[str, str]]:
    """
    Parse Terraform backend.tf to extract client and project info.

    Example backend.tf:
        terraform {
          backend "gcs" {
            bucket = "acme-corp-terraform-state"
            prefix = "app1/prod"
          }
        }

    Returns:
        dict with 'client' and 'project' keys, or None
    """
    if not backend_file.exists():
        return None

    try:
        content = backend_file.read_text()

        # Extract bucket name
        bucket_match = re.search(r'bucket\s*=\s*"([^"]+)"', content)
        if not bucket_match:
            return None

        bucket = bucket_match.group(1)

        # Extract prefix
        prefix_match = re.search(r'prefix\s*=\s*"([^"]+)"', content)
        if not prefix_match:
            return None

        prefix = prefix_match.group(1)

        # Parse bucket name: {client}-terraform-state
        # Parse prefix: {project}/{env}
        client = bucket.replace('-terraform-state', '')
        project = prefix.split('/')[0] if '/' in prefix else prefix

        return {
            'client': client,
            'project': project
        }

    except Exception:
        return None


def validate_platform_root(path: Path) -> bool:
    """
    Validate that a path is a valid platform root directory.

    Args:
        path: Path to validate

    Returns:
        True if valid platform root, False otherwise
    """
    if not path or not path.exists():
        return False

    # Check for required directories
    required_dirs = ['platform', 'modules', 'scripts']
    return all((path / d).exists() for d in required_dirs)


def get_platform_root() -> Optional[Path]:
    """
    Find the platform repository root directory.

    Checks (in order):
    1. SOLVIGO_PLATFORM_ROOT environment variable
    2. Walk up directory tree from current location
    3. ~/.solvigo/platform (future: for standalone CLI)

    Returns:
        Path to platform root, or None if not found
    """
    # 1. Check environment variable first
    platform_root_env = os.getenv('SOLVIGO_PLATFORM_ROOT')
    if platform_root_env:
        path = Path(platform_root_env).expanduser().resolve()
        if validate_platform_root(path):
            return path
        # If env var is set but invalid, warn but continue searching
        from rich.console import Console
        console = Console()
        console.print(f"[yellow]⚠ SOLVIGO_PLATFORM_ROOT is set but invalid: {path}[/yellow]")
        console.print("[dim]  Looking for platform root in current directory tree...[/dim]\n")

    # 2. Walk up the directory tree
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if validate_platform_root(parent):
            return parent

    # 3. Future: Check ~/.solvigo/platform for standalone CLI
    # home_platform = Path.home() / '.solvigo' / 'platform'
    # if validate_platform_root(home_platform):
    #     return home_platform

    return None


def find_client_projects(client: str) -> list[Dict[str, str]]:
    """
    Find all projects for a given client.

    Args:
        client: Client name

    Returns:
        List of dicts with project info
    """
    platform_root = get_platform_root()
    if not platform_root:
        return []

    clients_dir = platform_root / 'clients' / client
    if not clients_dir.exists():
        return []

    projects = []
    for project_dir in clients_dir.iterdir():
        if project_dir.is_dir() and not project_dir.name.startswith('.'):
            projects.append({
                'name': project_dir.name,
                'path': project_dir,
                'has_terraform': (project_dir / 'terraform').exists()
            })

    return projects


def list_all_clients() -> list[str]:
    """
    List all clients in the platform.

    Returns:
        List of client names
    """
    platform_root = get_platform_root()
    if not platform_root:
        return []

    clients_dir = platform_root / 'clients'
    if not clients_dir.exists():
        return []

    return [
        d.name
        for d in clients_dir.iterdir()
        if d.is_dir() and not d.name.startswith('.')
    ]

"""
Context detection - determines if CLI is running from a project directory
"""
import os
from pathlib import Path
import re
from typing import Dict, Optional


def detect_project_context(dev_mode: bool = False) -> Dict[str, any]:
    """
    Detect project by querying API with GitHub URL.

    This is the new architecture where the database is the source of truth.
    Projects are identified by their GitHub repository URL.

    Args:
        dev_mode: Whether to use local dev API (http://localhost:8081)

    Returns:
        dict: Context information with keys:
            - exists (bool): Whether a project was detected
            - client (str): Client ID from database
            - project (str): Project ID from database
            - github_url (str): GitHub repository URL
            - gcp_project_id (str): GCP project ID
            - project_data (dict): Full project details from API
            - error (str): Error message if detection failed
    """
    from solvigo.utils.git import get_git_remote_url

    # Get GitHub URL from git remote
    try:
        github_url = get_git_remote_url()
        if not github_url:
            return {
                'exists': False,
                'error': 'No git remote found. Run: git remote add origin <url>'
            }
    except Exception as e:
        return {
            'exists': False,
            'error': f'Git error: {e}'
        }

    # Query API for project with this GitHub URL
    try:
        from solvigo.admin.client import AdminClient

        client = AdminClient(dev_mode=dev_mode)
        projects = client.list_projects(github_repo=github_url)

        if not projects:
            return {
                'exists': False,
                'github_url': github_url,
                'error': 'No project found in registry for this repository.\nRun: solvigo init  to register this project.'
            }

        # Use first matching project
        project = projects[0]

        return {
            'exists': True,
            'client': project['client_id'],
            'project': project['id'],
            'github_url': github_url,
            'gcp_project_id': project.get('gcp_project_id'),
            'full_domain': project.get('full_domain'),
            'project_type': project.get('project_type'),
            'client_subdomain': project.get('client_subdomain'),
            'project_subdomain': project.get('subdomain'),
            'project_data': project  # Full project details from API
        }

    except Exception as e:
        return {
            'exists': False,
            'github_url': github_url,
            'error': f'API error: {e}\nTip: Run with --dev flag to use local API'
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

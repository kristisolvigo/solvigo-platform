"""
Git repository detection and management
"""
import subprocess
from pathlib import Path
from typing import Optional, Dict
from rich.console import Console

console = Console()


def check_git_repo() -> Optional[Dict[str, str]]:
    """
    Check if current directory is in a git repository.

    Returns:
        Dict with git info if in repo, None otherwise
    """
    try:
        # Check if in git repo
        result = subprocess.run(
            ['git', 'rev-parse', '--is-inside-work-tree'],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )

        if result.returncode != 0:
            return None

        # Get repo root
        root_result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )

        repo_root = root_result.stdout.strip()

        # Get current branch
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )

        branch = branch_result.stdout.strip()

        # Get remote URL if available
        remote_result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )

        remote = remote_result.stdout.strip() if remote_result.returncode == 0 else None

        # Check for uncommitted changes
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )

        has_changes = bool(status_result.stdout.strip())

        return {
            'root': repo_root,
            'branch': branch,
            'remote': remote,
            'has_changes': has_changes
        }

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def verify_git_repo_or_exit() -> Dict[str, str]:
    """
    Verify we're in a git repository or exit.

    Returns:
        Git repository info

    Exits if not in a git repo.
    """
    from rich.panel import Panel
    from solvigo.ui.prompts import confirm_action

    git_info = check_git_repo()

    if not git_info:
        console.print()
        console.print(Panel(
            "[red]✗ Not in a git repository[/red]\n\n"
            "The Solvigo CLI requires a git repository for:\n"
            "  • Tracking infrastructure changes\n"
            "  • Version control for Terraform configs\n"
            "  • Cloud Build integration\n\n"
            "[yellow]Please initialize a git repository:[/yellow]\n"
            "  git init\n"
            "  git remote add origin <your-repo-url>",
            title="Git Repository Required",
            border_style="red"
        ))
        console.print()
        exit(1)

    # Show git info
    console.print()
    console.print("[bold cyan]Git Repository Detected[/bold cyan]")
    console.print(f"  📁 Root:   [dim]{git_info['root']}[/dim]")
    console.print(f"  🌿 Branch: [cyan]{git_info['branch']}[/cyan]")

    if git_info['remote']:
        console.print(f"  🔗 Remote: [dim]{git_info['remote']}[/dim]")
    else:
        console.print(f"  🔗 Remote: [yellow]Not configured[/yellow]")

    if git_info['has_changes']:
        console.print(f"  📝 Status: [yellow]Uncommitted changes[/yellow]")
    else:
        console.print(f"  📝 Status: [green]Clean[/green]")

    console.print()

    # Confirm to proceed
    if not confirm_action("Continue with this repository?", default=True):
        console.print("\n[yellow]Exiting...[/yellow]\n")
        exit(0)

    return git_info


def get_git_remote_url() -> Optional[str]:
    """
    Get the GitHub URL from git remote, normalized to HTTPS format.

    Returns:
        Normalized GitHub URL (HTTPS, without .git suffix) or None

    Examples:
        git@github.com:Solvigo/repo.git -> https://github.com/Solvigo/repo
        https://github.com/Solvigo/repo.git -> https://github.com/Solvigo/repo
    """
    try:
        result = subprocess.run(
            ['git', 'config', '--get', 'remote.origin.url'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        url = result.stdout.strip()

        if not url:
            return None

        # Normalize URL (handle both SSH and HTTPS)
        # git@github.com:Solvigo/repo.git -> https://github.com/Solvigo/repo
        # https://github.com/Solvigo/repo.git -> https://github.com/Solvigo/repo
        if url.startswith('git@github.com:'):
            url = url.replace('git@github.com:', 'https://github.com/')

        # Remove .git suffix
        if url.endswith('.git'):
            url = url[:-4]

        return url

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

"""
GCP Folder management - create client folders and organize projects
"""
import subprocess
import json
from typing import Optional
from rich.console import Console
from solvigo.ui.prompts import confirm_action

console = Console()


def find_folder_by_name(folder_name: str, parent_folder_id: str) -> Optional[str]:
    """
    Search for folder by display name under parent.

    Args:
        folder_name: Folder display name to search for
        parent_folder_id: Parent folder ID (e.g., '212465532368')

    Returns:
        Folder ID if found, None otherwise
    """
    try:
        result = subprocess.run(
            [
                'gcloud', 'resource-manager', 'folders', 'list',
                f'--folder={parent_folder_id}',
                '--format=json',
                '--verbosity=error'
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )

        if result.returncode != 0:
            return None

        folders = json.loads(result.stdout) if result.stdout else []

        # Search for matching folder (case-insensitive)
        for folder in folders:
            if folder.get('displayName', '').lower() == folder_name.lower():
                # Extract folder ID from name (format: folders/123456789)
                folder_full_name = folder.get('name', '')
                if '/' in folder_full_name:
                    return folder_full_name.split('/')[1]

        return None

    except Exception as e:
        console.print(f"[yellow]⚠ Error searching for folder: {e}[/yellow]")
        return None


def create_folder(folder_name: str, parent_folder_id: str) -> Optional[str]:
    """
    Create a new folder under parent.

    Args:
        folder_name: Display name for new folder
        parent_folder_id: Parent folder ID

    Returns:
        New folder ID if successful, None otherwise
    """
    try:
        console.print(f"[cyan]Creating folder '{folder_name}'...[/cyan]")

        result = subprocess.run(
            [
                'gcloud', 'resource-manager', 'folders', 'create',
                f'--display-name={folder_name}',
                f'--folder={parent_folder_id}',
                '--format=json'
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )

        # Parse response to get folder ID
        folder_data = json.loads(result.stdout)
        folder_full_name = folder_data.get('name', '')

        if '/' in folder_full_name:
            folder_id = folder_full_name.split('/')[1]
            console.print(f"[green]✓ Folder created: {folder_id}[/green]")
            return folder_id

        return None

    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to create folder: {e.stderr}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]✗ Error creating folder: {e}[/red]")
        return None


def get_or_create_client_folder(client_name: str, parent_folder_id: str) -> Optional[str]:
    """
    Get existing client folder or create new one.

    Args:
        client_name: Client name (will be lowercased for folder name)
        parent_folder_id: Solvigo parent folder ID

    Returns:
        Folder ID if successful, None if creation fails or user declines
    """
    # Normalize folder name to lowercase
    folder_name = client_name.lower()

    console.print(f"\n[cyan]Checking for client folder: {folder_name}[/cyan]")

    # Check if folder already exists
    existing_folder_id = find_folder_by_name(folder_name, parent_folder_id)

    if existing_folder_id:
        console.print(f"[green]✓ Found existing folder: {existing_folder_id}[/green]\n")
        return existing_folder_id

    # Folder doesn't exist - ask to create
    console.print(f"[yellow]Client folder '{folder_name}' does not exist.[/yellow]\n")

    if not confirm_action(f"Create folder '{folder_name}' under Solvigo organization?", default=True):
        console.print("[yellow]Skipping folder creation[/yellow]\n")
        return None

    # Create new folder
    new_folder_id = create_folder(folder_name, parent_folder_id)

    if new_folder_id:
        console.print()
        return new_folder_id
    else:
        console.print("\n[red]Could not create folder. Check permissions:[/red]")
        console.print("[dim]  - resourcemanager.folderAdmin[/dim]")
        console.print("[dim]  - Ensure you have permissions at folder level[/dim]\n")
        return None


def move_project_to_folder(project_id: str, folder_id: str) -> bool:
    """
    Move GCP project into specified folder.

    Args:
        project_id: GCP project ID to move
        folder_id: Target folder ID

    Returns:
        True if successful or already in folder, False if failed
    """
    try:
        # Check current parent
        result = subprocess.run(
            [
                'gcloud', 'projects', 'describe', project_id,
                '--format=json',
                '--verbosity=error'
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )

        if result.returncode == 0:
            project_data = json.loads(result.stdout)
            current_parent = project_data.get('parent', {})

            # Check if already in target folder
            if current_parent.get('type') == 'folder' and current_parent.get('id') == folder_id:
                console.print(f"[dim]Project already in folder {folder_id}[/dim]")
                return True

        # Move project to folder (requires beta command)
        console.print(f"[cyan]Moving project to folder...[/cyan]")

        result = subprocess.run(
            [
                'gcloud', 'beta', 'projects', 'move', project_id,
                f'--folder={folder_id}',
                '--quiet'  # Auto-accept the confirmation prompt
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60
        )

        if result.returncode == 0:
            console.print(f"[green]✓ Project moved to folder[/green]")
            return True
        else:
            console.print(f"[yellow]⚠ Could not move project: {result.stderr}[/yellow]")
            return False

    except Exception as e:
        console.print(f"[red]✗ Error moving project: {e}[/red]")
        return False


def list_client_folders(parent_folder_id: str) -> list:
    """
    List all client folders under Solvigo parent folder.

    Args:
        parent_folder_id: Parent folder ID

    Returns:
        List of dicts with folder info (id, name)
    """
    try:
        result = subprocess.run(
            [
                'gcloud', 'resource-manager', 'folders', 'list',
                f'--folder={parent_folder_id}',
                '--format=json',
                '--verbosity=error'
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )

        folders = json.loads(result.stdout) if result.stdout else []

        return [
            {
                'id': f.get('name', '').split('/')[1] if '/' in f.get('name', '') else None,
                'name': f.get('displayName', ''),
                'full_name': f.get('name', '')
            }
            for f in folders
        ]

    except Exception as e:
        console.print(f"[yellow]⚠ Error listing folders: {e}[/yellow]")
        return []

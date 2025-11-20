"""
Terraform runner - execute terraform commands and stream output
"""
import subprocess
import os
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text

console = Console()


def run_terraform(
    working_dir: Path,
    command: str,
    auto_approve: bool = False,
    var_file: Optional[Path] = None
) -> bool:
    """
    Run a terraform command and stream output.

    Args:
        working_dir: Directory containing Terraform files
        command: Terraform command (init, plan, apply, destroy)
        auto_approve: Auto-approve for apply/destroy
        var_file: Optional path to tfvars file

    Returns:
        True if successful, False otherwise
    """
    if not working_dir.exists():
        console.print(f"[red]✗ Directory not found: {working_dir}[/red]\n")
        return False

    # Build command
    cmd = ['terraform', command]

    if command in ['apply', 'destroy'] and auto_approve:
        cmd.append('-auto-approve')

    if var_file and var_file.exists():
        cmd.extend(['-var-file', str(var_file)])

    console.print(f"\n[cyan]Running: {' '.join(cmd)}[/cyan]")
    console.print(f"[dim]Directory: {working_dir}[/dim]\n")

    try:
        # Run terraform with live output
        process = subprocess.Popen(
            cmd,
            cwd=str(working_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Stream output
        for line in process.stdout:
            # Color code terraform output
            if line.strip().startswith('+'):
                console.print(f"[green]{line.rstrip()}[/green]")
            elif line.strip().startswith('-'):
                console.print(f"[red]{line.rstrip()}[/red]")
            elif line.strip().startswith('~'):
                console.print(f"[yellow]{line.rstrip()}[/yellow]")
            elif 'Error' in line or 'error' in line:
                console.print(f"[red]{line.rstrip()}[/red]")
            elif 'Warning' in line or 'warning' in line:
                console.print(f"[yellow]{line.rstrip()}[/yellow]")
            else:
                console.print(line.rstrip())

        process.wait()

        if process.returncode == 0:
            console.print(f"\n[green]✓ {command} completed successfully[/green]\n")
            return True
        else:
            console.print(f"\n[red]✗ {command} failed with code {process.returncode}[/red]\n")
            return False

    except FileNotFoundError:
        console.print("[red]✗ Terraform not found. Please install Terraform >= 1.5.0[/red]\n")
        return False
    except Exception as e:
        console.print(f"[red]✗ Error running terraform: {e}[/red]\n")
        return False


def terraform_init(working_dir: Path) -> bool:
    """Run terraform init"""
    return run_terraform(working_dir, 'init')


def terraform_plan(working_dir: Path) -> bool:
    """Run terraform plan"""
    return run_terraform(working_dir, 'plan')


def terraform_apply(working_dir: Path, auto_approve: bool = False) -> bool:
    """Run terraform apply"""
    return run_terraform(working_dir, 'apply', auto_approve=auto_approve)


def terraform_destroy(working_dir: Path, auto_approve: bool = False) -> bool:
    """Run terraform destroy"""
    return run_terraform(working_dir, 'destroy', auto_approve=auto_approve)


def ensure_state_bucket(bucket_name: str, project_id: str, region: str = 'europe-north1') -> bool:
    """
    Ensure Terraform state bucket exists. Create if needed.

    Args:
        bucket_name: GCS bucket name
        project_id: GCP project ID
        region: Bucket location

    Returns:
        True if exists or created successfully
    """
    # Check if bucket exists
    result = subprocess.run(
        ['gcloud', 'storage', 'buckets', 'describe', f'gs://{bucket_name}',
         '--format=json', '--verbosity=error'],
        capture_output=True,
        check=False,
        timeout=10
    )

    if result.returncode == 0:
        console.print(f"  [dim]State bucket exists: {bucket_name}[/dim]")
        return True

    # Bucket doesn't exist - create it
    console.print(f"  [cyan]Creating Terraform state bucket: {bucket_name}...[/cyan]")

    result = subprocess.run(
        [
            'gcloud', 'storage', 'buckets', 'create', f'gs://{bucket_name}',
            f'--project={project_id}',
            f'--location={region}',
            '--uniform-bucket-level-access'
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30
    )

    if result.returncode == 0:
        console.print(f"  [green]✓ State bucket created: {bucket_name}[/green]")
        return True
    else:
        console.print(f"  [red]✗ Failed to create bucket: {result.stderr}[/red]")
        return False


def check_terraform_installed() -> bool:
    """
    Check if Terraform is installed.

    Returns:
        True if installed, False otherwise
    """
    try:
        result = subprocess.run(
            ['terraform', 'version'],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )

        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            console.print(f"[green]✓ {version_line}[/green]")
            return True
        else:
            return False

    except FileNotFoundError:
        console.print("[red]✗ Terraform not installed[/red]")
        console.print("[yellow]Install: https://www.terraform.io/downloads[/yellow]\n")
        return False
    except Exception:
        return False


# Aliases for consistency with CLI code
def run_terraform_plan(terraform_dir: Path) -> bool:
    """Run terraform plan (alias for terraform_plan)"""
    return terraform_plan(terraform_dir)


def run_terraform_apply(terraform_dir: Path) -> bool:
    """Run terraform apply interactively (alias for terraform_apply)"""
    return terraform_apply(terraform_dir, auto_approve=False)


def run_terraform_import_workflow(terraform_dir: Path, gcp_project_id: str = None) -> bool:
    """
    Run the full Terraform import workflow.

    Args:
        terraform_dir: Path to terraform directory
        gcp_project_id: GCP project ID (for creating state bucket if needed)

    Returns:
        True if successful
    """
    from solvigo.ui.prompts import confirm_action
    import re

    console.print(Panel(
        "[bold]Terraform Import Workflow[/bold]\n\n"
        "This will:\n"
        "  1. Initialize Terraform\n"
        "  2. Run terraform plan (preview imports)\n"
        "  3. Run terraform apply (execute imports)",
        title="Import Workflow",
        border_style="cyan"
    ))
    console.print()

    if not confirm_action("Proceed with import workflow?", default=True):
        return False

    # Step 0: Ensure state bucket exists
    if gcp_project_id:
        backend_file = terraform_dir / 'backend.tf'
        if backend_file.exists():
            console.print("\n[cyan]Checking Terraform state bucket...[/cyan]\n")

            content = backend_file.read_text()
            match = re.search(r'bucket\s*=\s*"([^"]+)"', content)

            if match:
                bucket_name = match.group(1)

                if not ensure_state_bucket(bucket_name, gcp_project_id):
                    console.print("[yellow]⚠ Could not create state bucket[/yellow]")
                    if not confirm_action("Continue anyway (terraform init may fail)?", default=False):
                        return False

    # Step 1: Init
    console.print("[bold cyan]Step 1/3: Terraform Init[/bold cyan]\n")
    if not terraform_init(terraform_dir):
        console.print("[red]✗ Init failed[/red]\n")
        return False

    # Step 2: Plan
    console.print("\n[bold cyan]Step 2/3: Terraform Plan[/bold cyan]\n")
    if not terraform_plan(terraform_dir):
        console.print("[red]✗ Plan failed[/red]\n")
        return False

    # Ask for confirmation before apply
    console.print()
    if not confirm_action("Apply these changes and import resources?", default=True):
        console.print("\n[yellow]Import cancelled. You can run 'terraform apply' manually later.[/yellow]\n")
        return False

    # Step 3: Apply
    console.print("\n[bold cyan]Step 3/3: Terraform Apply[/bold cyan]\n")
    if not terraform_apply(terraform_dir, auto_approve=False):
        console.print("[red]✗ Apply failed[/red]\n")
        return False

    console.print("\n[green]✓ Import workflow completed successfully![/green]\n")
    return True

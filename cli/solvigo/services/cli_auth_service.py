"""
CLI Authentication service

Handles authentication for CLI operations using gcloud.
"""
import subprocess
from typing import Optional
from rich.console import Console

console = Console()


class CLIAuthService:
    """Service for CLI authentication."""

    @staticmethod
    def verify_gcloud_auth() -> bool:
        """
        Check if user is authenticated with gcloud.

        Returns:
            True if authenticated, False otherwise
        """
        try:
            result = subprocess.run(
                ['gcloud', 'auth', 'list', '--filter=status:ACTIVE', '--format=value(account)'],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    @staticmethod
    def get_current_user() -> str:
        """
        Get the currently authenticated gcloud user email.

        Returns:
            User email

        Raises:
            Exception if no active auth
        """
        result = subprocess.run(
            ['gcloud', 'auth', 'list', '--filter=status:ACTIVE', '--format=value(account)'],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
        return result.stdout.strip()

    @staticmethod
    def prompt_login():
        """Prompt user to login with gcloud."""
        console.print("\n[yellow]⚠ Not authenticated with Google Cloud[/yellow]\n")
        console.print("Please login to continue:\n")

        try:
            subprocess.run(['gcloud', 'auth', 'login'], check=True)
            console.print("[green]✓ Authentication successful![/green]\n")
        except subprocess.CalledProcessError:
            console.print("[red]✗ Authentication failed.[/red]")
            raise Exception("Failed to authenticate with gcloud")

    @classmethod
    def ensure_authenticated(cls) -> str:
        """
        Ensure user is authenticated, prompt if not.

        Returns:
            User email

        Raises:
            Exception if authentication fails
        """
        if not cls.verify_gcloud_auth():
            cls.prompt_login()

        user_email = cls.get_current_user()
        if not user_email:
            raise Exception("Could not determine authenticated user")

        return user_email

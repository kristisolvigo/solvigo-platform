"""
Configuration management for Solvigo CLI
"""
import os
from pathlib import Path
from typing import Optional


class Config:
    """Global configuration for Solvigo CLI"""

    def __init__(self):
        self.load_from_env()

    def load_from_env(self):
        """Load configuration from environment variables"""
        self.org_id = os.getenv('SOLVIGO_ORG_ID')
        self.billing_account = os.getenv('SOLVIGO_BILLING_ACCOUNT')
        self.folder_id = os.getenv('SOLVIGO_FOLDER_ID')
        self.platform_project = os.getenv('SOLVIGO_PLATFORM_PROJECT', 'solvigo-platform-prod')
        self.state_bucket = os.getenv('SOLVIGO_STATE_BUCKET', 'solvigo-platform-terraform-state')
        self.region = os.getenv('SOLVIGO_REGION', 'europe-north2')
        self.domain = os.getenv('SOLVIGO_DOMAIN', 'solvigo.ai')

    def validate(self) -> bool:
        """
        Validate that required configuration is present.

        Returns:
            True if valid, False otherwise
        """
        required = ['org_id', 'billing_account', 'folder_id']

        missing = [field for field in required if not getattr(self, field)]

        if missing:
            return False

        return True

    def get_platform_root(self) -> Optional[Path]:
        """Get the platform repository root."""
        from solvigo.utils.context import get_platform_root
        return get_platform_root()


# Global config instance
config = Config()

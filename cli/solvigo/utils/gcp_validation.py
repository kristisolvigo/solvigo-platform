"""
GCP project ID validation utilities

Provides validation and sanitization for GCP project IDs according to GCP requirements.
"""
import re
from typing import Tuple, Optional


class GCPProjectIDValidator:
    """Validates GCP project IDs against GCP requirements."""

    MIN_LENGTH = 6
    MAX_LENGTH = 30
    VALID_PATTERN = re.compile(r'^[a-z][a-z0-9-]*[a-z0-9]$')
    RESERVED_WORDS = ['google', 'goog', 'ssl', 'default', 'test']

    @classmethod
    def validate(cls, project_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate GCP project ID against all GCP requirements.

        Requirements:
        - 6-30 characters
        - Lowercase letters, digits, and hyphens only
        - Must start with a letter
        - Cannot end with a hyphen

        Args:
            project_id: Project ID to validate

        Returns:
            (is_valid, error_message) - error_message is None if valid
        """
        if not project_id:
            return False, "Project ID cannot be empty"

        if len(project_id) < cls.MIN_LENGTH:
            return False, f"Too short (minimum {cls.MIN_LENGTH} characters)"

        if len(project_id) > cls.MAX_LENGTH:
            return False, f"Too long (maximum {cls.MAX_LENGTH} characters)"

        if not project_id[0].isalpha():
            return False, "Must start with a lowercase letter"

        if project_id[-1] == '-':
            return False, "Cannot end with a hyphen"

        if not project_id.islower():
            return False, "Must be all lowercase"

        if not cls.VALID_PATTERN.match(project_id):
            return False, "Can only contain lowercase letters, digits, and hyphens"

        if any(word in project_id for word in cls.RESERVED_WORDS):
            return False, f"Cannot contain reserved words: {', '.join(cls.RESERVED_WORDS)}"

        return True, None

    @classmethod
    def sanitize(cls, name: str) -> str:
        """
        Sanitize a name to create a valid project ID base.

        Note: This does NOT guarantee a valid ID - you may still need to:
        - Truncate if too long
        - Add suffix for uniqueness
        - Validate the final result

        Args:
            name: Input name to sanitize

        Returns:
            Sanitized name suitable for use in project ID
        """
        # Convert to lowercase
        sanitized = name.lower()

        # Replace spaces and underscores with hyphens
        sanitized = sanitized.replace(' ', '-').replace('_', '-')

        # Remove invalid characters (keep only a-z, 0-9, -)
        sanitized = re.sub(r'[^a-z0-9-]', '', sanitized)

        # Collapse multiple hyphens into single hyphen
        sanitized = re.sub(r'-+', '-', sanitized)

        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')

        # Ensure starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'p-' + sanitized

        return sanitized

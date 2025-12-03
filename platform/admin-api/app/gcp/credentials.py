"""
GCP credential provider for Admin API.

Handles credential management for both local dev and production:
- Local dev: Uses service account key file
- Production: Uses Cloud Run service account
"""
import os
import logging
import google.auth
from google.oauth2 import service_account
from google.auth.credentials import Credentials
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

PLATFORM_PROJECT_ID = "solvigo-platform-prod"
SERVICE_ACCOUNT_EMAIL = "registry-api@solvigo-platform-prod.iam.gserviceaccount.com"


def get_credentials(scopes: Optional[list] = None) -> Tuple[Credentials, str]:
    """
    Get GCP credentials for Admin API operations.

    In dev mode: Uses service account key file from GOOGLE_APPLICATION_CREDENTIALS
    In production: Uses the Cloud Run service account

    Args:
        scopes: OAuth scopes (default: cloud-platform)

    Returns:
        Tuple of (credentials, project_id)

    Raises:
        google.auth.exceptions.DefaultCredentialsError: If credentials unavailable
    """
    dev_mode = os.getenv('DEV_MODE', 'false').lower() == 'true'

    if scopes is None:
        scopes = ['https://www.googleapis.com/auth/cloud-platform']

    if dev_mode:
        # Use service account key file for local development
        key_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

        if not key_path or not os.path.exists(key_path):
            logger.error(f"Service account key file not found at: {key_path}")
            raise FileNotFoundError(
                f"Service account key file not found. "
                f"Please set GOOGLE_APPLICATION_CREDENTIALS to point to the key file."
            )

        logger.info(f"DEV MODE: Using service account key file: {key_path}")
        credentials = service_account.Credentials.from_service_account_file(
            key_path,
            scopes=scopes
        )
        logger.info(f"Authenticated as: {SERVICE_ACCOUNT_EMAIL}")
        return credentials, PLATFORM_PROJECT_ID

    else:
        # Production: Use default credentials (Cloud Run SA)
        logger.info("PRODUCTION: Using default credentials")
        credentials, project = google.auth.default(scopes=scopes)
        return credentials, project or PLATFORM_PROJECT_ID


def get_credentials_for_client(client_class, **kwargs):
    """
    Get credentials and initialize a GCP client.

    Args:
        client_class: GCP client class (e.g., cloudbuild_v1.CloudBuildClient)
        **kwargs: Additional arguments for client initialization

    Returns:
        Initialized GCP client with appropriate credentials

    Example:
        build_client = get_credentials_for_client(cloudbuild_v1.CloudBuildClient)
    """
    credentials, project = get_credentials()
    return client_class(credentials=credentials, **kwargs)

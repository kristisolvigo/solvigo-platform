"""GCP IAM authentication for API endpoints"""
from fastapi import Header, HTTPException, Depends
from google.oauth2 import id_token
from google.auth.transport import requests
import logging

logger = logging.getLogger(__name__)


async def verify_gcp_token(authorization: str = Header(...)) -> str:
    """
    Verify GCP ID token and return user email.

    Args:
        authorization: Authorization header (Bearer token)

    Returns:
        User email from verified token

    Raises:
        HTTPException: If token is invalid or missing
    """
    try:
        # Extract token from "Bearer <token>" format
        if not authorization.startswith('Bearer '):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header format. Expected 'Bearer <token>'"
            )

        token = authorization.replace('Bearer ', '')

        # Verify the ID token
        id_info = id_token.verify_oauth2_token(
            token,
            requests.Request()
        )

        # Extract email
        email = id_info.get('email')
        if not email:
            raise HTTPException(
                status_code=401,
                detail="Token does not contain email"
            )

        logger.info(f"Authenticated user: {email}")
        return email

    except ValueError as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )


def get_current_user(email: str = Depends(verify_gcp_token)) -> str:
    """Dependency to get current authenticated user email"""
    return email

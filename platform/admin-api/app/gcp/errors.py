"""
Centralized GCP error handling for platform operations.

This module provides utilities to convert GCP API exceptions into
structured HTTP responses with detailed error information.
"""
from fastapi import HTTPException
from google.api_core import exceptions as google_exceptions
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class GCPErrorDetail:
    """Structured error detail for GCP operations"""

    def __init__(
        self,
        error_type: str,
        message: str,
        gcp_error_code: Optional[str] = None,
        required_permissions: Optional[List[str]] = None,
        remediation: Optional[str] = None,
        resource_name: Optional[str] = None
    ):
        self.error_type = error_type
        self.message = message
        self.gcp_error_code = gcp_error_code
        self.required_permissions = required_permissions
        self.remediation = remediation
        self.resource_name = resource_name

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON response"""
        detail = {
            "error_type": self.error_type,
            "message": self.message
        }
        if self.gcp_error_code:
            detail["gcp_error_code"] = self.gcp_error_code
        if self.required_permissions:
            detail["required_permissions"] = self.required_permissions
        if self.remediation:
            detail["remediation"] = self.remediation
        if self.resource_name:
            detail["resource_name"] = self.resource_name
        return detail


def handle_gcp_error(
    error: Exception,
    operation: str,
    resource_name: Optional[str] = None
) -> HTTPException:
    """
    Convert GCP exceptions to structured HTTPException.

    Args:
        error: The caught exception
        operation: Description of the operation being performed
        resource_name: Name/ID of the resource being operated on

    Returns:
        HTTPException with structured error detail
    """

    # AlreadyExists - Resource already exists (idempotent case)
    if isinstance(error, google_exceptions.AlreadyExists):
        logger.info(f"{operation}: Resource already exists - {resource_name}")
        error_detail = GCPErrorDetail(
            error_type="AlreadyExists",
            message=f"Resource already exists: {resource_name or 'unnamed'}",
            gcp_error_code=str(error.code) if hasattr(error, 'code') else None,
            remediation="Resource already exists. This is normal for idempotent operations.",
            resource_name=resource_name
        )
        return HTTPException(status_code=409, detail=error_detail.to_dict())

    # PermissionDenied - Insufficient IAM permissions
    elif isinstance(error, google_exceptions.PermissionDenied):
        logger.error(f"{operation}: Permission denied - {error}")
        error_detail = GCPErrorDetail(
            error_type="PermissionDenied",
            message="Admin API service account lacks required permissions",
            gcp_error_code=str(error.code) if hasattr(error, 'code') else None,
            remediation="Contact platform administrator to grant required IAM roles",
            resource_name=resource_name
        )
        return HTTPException(status_code=403, detail=error_detail.to_dict())

    # NotFound - Resource not found
    elif isinstance(error, google_exceptions.NotFound):
        logger.error(f"{operation}: Resource not found - {resource_name}")
        error_detail = GCPErrorDetail(
            error_type="NotFound",
            message=f"Resource not found: {resource_name or 'unnamed'}",
            gcp_error_code=str(error.code) if hasattr(error, 'code') else None,
            remediation="Verify the resource name/ID is correct",
            resource_name=resource_name
        )
        return HTTPException(status_code=404, detail=error_detail.to_dict())

    # InvalidArgument - Bad request parameters
    elif isinstance(error, google_exceptions.InvalidArgument):
        logger.error(f"{operation}: Invalid argument - {error}")
        error_detail = GCPErrorDetail(
            error_type="InvalidArgument",
            message=f"Invalid request parameters: {str(error)}",
            gcp_error_code=str(error.code) if hasattr(error, 'code') else None,
            remediation="Check the request parameters and try again",
            resource_name=resource_name
        )
        return HTTPException(status_code=400, detail=error_detail.to_dict())

    # FailedPrecondition - Operation cannot be performed in current state
    elif isinstance(error, google_exceptions.FailedPrecondition):
        logger.error(f"{operation}: Failed precondition - {error}")
        error_detail = GCPErrorDetail(
            error_type="FailedPrecondition",
            message=f"Operation cannot be performed: {str(error)}",
            gcp_error_code=str(error.code) if hasattr(error, 'code') else None,
            remediation="Verify that prerequisite operations have completed",
            resource_name=resource_name
        )
        return HTTPException(status_code=400, detail=error_detail.to_dict())

    # DeadlineExceeded - Operation timeout
    elif isinstance(error, google_exceptions.DeadlineExceeded):
        logger.error(f"{operation}: Timeout - {error}")
        error_detail = GCPErrorDetail(
            error_type="DeadlineExceeded",
            message="Operation timed out",
            gcp_error_code=str(error.code) if hasattr(error, 'code') else None,
            remediation="Try again. Some operations (like API enablement) can take several minutes.",
            resource_name=resource_name
        )
        return HTTPException(status_code=504, detail=error_detail.to_dict())

    # ResourceExhausted - Quota exceeded
    elif isinstance(error, google_exceptions.ResourceExhausted):
        logger.error(f"{operation}: Quota exceeded - {error}")
        error_detail = GCPErrorDetail(
            error_type="ResourceExhausted",
            message="GCP quota or rate limit exceeded",
            gcp_error_code=str(error.code) if hasattr(error, 'code') else None,
            remediation="Wait and retry, or request quota increase",
            resource_name=resource_name
        )
        return HTTPException(status_code=429, detail=error_detail.to_dict())

    # Unauthenticated - Missing or invalid credentials
    elif isinstance(error, google_exceptions.Unauthenticated):
        logger.error(f"{operation}: Authentication failed - {error}")
        error_detail = GCPErrorDetail(
            error_type="Unauthenticated",
            message="GCP authentication failed",
            gcp_error_code=str(error.code) if hasattr(error, 'code') else None,
            remediation="Verify Admin API service account credentials",
            resource_name=resource_name
        )
        return HTTPException(status_code=401, detail=error_detail.to_dict())

    # Generic GoogleAPICallError
    elif isinstance(error, google_exceptions.GoogleAPICallError):
        logger.error(f"{operation}: GCP API error - {error}")
        error_detail = GCPErrorDetail(
            error_type="GoogleAPIError",
            message=f"GCP API error: {str(error)}",
            gcp_error_code=str(error.code) if hasattr(error, 'code') else None,
            remediation="Check GCP service status and try again",
            resource_name=resource_name
        )
        return HTTPException(status_code=500, detail=error_detail.to_dict())

    # Unexpected error
    else:
        logger.error(f"{operation}: Unexpected error - {type(error).__name__}: {error}")
        error_detail = GCPErrorDetail(
            error_type=type(error).__name__,
            message=f"Unexpected error: {str(error)}",
            remediation="Contact platform administrator",
            resource_name=resource_name
        )
        return HTTPException(status_code=500, detail=error_detail.to_dict())


def idempotent_operation(func):
    """
    Decorator for idempotent GCP operations.

    If the operation raises AlreadyExists, logs it and continues.
    Useful for operations that should succeed even if resource exists.

    Usage:
        @idempotent_operation
        def create_resource(...):
            # GCP creation call
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except google_exceptions.AlreadyExists as e:
            logger.info(f"Resource already exists (idempotent): {e}")
            # Return None to indicate resource already exists
            return None
    return wrapper

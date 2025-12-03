"""Project lookup service"""
from typing import Optional
from enum import Enum
from dataclasses import dataclass

from solvigo.domain.entities import ProjectInfo, GitRepoInfo, Environment, Service


class ProjectLookupResult(Enum):
    """Result of project lookup operation"""
    FOUND = "found"
    NOT_FOUND = "not_found"
    NEEDS_BILLING = "needs_billing"
    API_ERROR = "api_error"


@dataclass
class LookupResponse:
    """Response from project lookup operation"""
    result: ProjectLookupResult
    project: Optional[ProjectInfo] = None
    error_message: Optional[str] = None


class ProjectLookupService:
    """Service for looking up projects from the database"""

    def __init__(self, admin_client):
        """
        Initialize the service.

        Args:
            admin_client: AdminClient instance for API communication
        """
        self.admin_client = admin_client

    def lookup_by_git_repo(self, git_info: GitRepoInfo) -> LookupResponse:
        """
        Look up project by git remote URL.

        Args:
            git_info: Git repository information

        Returns:
            LookupResponse with result status and project info if found
        """
        if not git_info.remote:
            return LookupResponse(
                result=ProjectLookupResult.NOT_FOUND,
                error_message="No git remote configured"
            )

        try:
            # Query API with github_repo filter
            projects = self.admin_client.list_projects(github_repo=git_info.remote)

            if not projects:
                return LookupResponse(result=ProjectLookupResult.NOT_FOUND)

            # Get full project details
            project_id = projects[0]['id']
            project_detail = self.admin_client.get_project(project_id)
            project_info = self._map_to_entity(project_detail)

            # Check billing status
            if project_info.needs_billing:
                return LookupResponse(
                    result=ProjectLookupResult.NEEDS_BILLING,
                    project=project_info
                )

            return LookupResponse(
                result=ProjectLookupResult.FOUND,
                project=project_info
            )

        except Exception as e:
            return LookupResponse(
                result=ProjectLookupResult.API_ERROR,
                error_message=str(e)
            )

    def _map_to_entity(self, api_response: dict) -> ProjectInfo:
        """Map API response to domain entity"""
        environments = [
            Environment(
                name=env['name'],
                database_instance=env.get('database_instance'),
                auto_deploy=env.get('auto_deploy', False),
                requires_approval=env.get('requires_approval', True)
            )
            for env in api_response.get('environments', [])
        ]

        services = [
            Service(
                name=svc['name'],
                type=svc['type'],
                cloud_run_service=svc.get('cloud_run_service'),
                cloud_run_url=svc.get('cloud_run_url'),
                status=svc.get('status', 'unknown'),
                last_deployed_at=svc.get('last_deployed_at')
            )
            for svc in api_response.get('services', [])
        ]

        return ProjectInfo(
            id=api_response['id'],
            client_id=api_response['client_id'],
            name=api_response['name'],
            gcp_project_id=api_response.get('gcp_project_id'),
            full_domain=api_response.get('full_domain'),
            github_repo=api_response.get('github_repo'),
            status=api_response.get('status', 'active'),
            environments=environments,
            services=services,
            gcp_region=api_response.get('gcp_region'),
            terraform_state_bucket=api_response.get('terraform_state_bucket'),
            last_deployed_at=api_response.get('last_deployed_at'),
            client_subdomain=api_response.get('client_subdomain'),
            project_subdomain=api_response.get('subdomain')
        )

"""
Registry API client for CLI to register and query projects
"""
import os
import requests
from typing import Dict, List, Optional
from rich.console import Console

console = Console()


class AdminClient:
    """Client for interacting with Solvigo Admin API"""

    def __init__(self, dev_mode: bool = False):
        self.dev_mode = dev_mode
        if dev_mode:
            self.api_url = "http://localhost:8081"
        else:
            self.api_url = os.getenv(
                'SOLVIGO_ADMIN_API_URL',
                'https://admin-api-430162142300.europe-north1.run.app'
            )
        self.base_url = f"{self.api_url}/api/v1"
        self._token = None

    def _get_auth_token(self) -> Optional[str]:
        """Get GCP ID token for authenticating to Cloud Run"""
        # Auth is now required in all modes (dev and prod)
        if self._token:
            return self._token

        try:
            import subprocess
            result = subprocess.run(
                [
                    'gcloud', 'auth', 'print-identity-token',
                    f'--audiences={self.api_url}'
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            self._token = result.stdout.strip()
            return self._token
        except Exception as e:
            raise Exception(f"Failed to get auth token: {e}")

    def _make_request(self, method: str, endpoint: str, data: Dict = None, require_auth: bool = True, timeout: int = 30) -> Dict:
        """Make HTTP request to registry API"""
        url = f"{self.base_url}/{endpoint}"
        headers = {}

        if require_auth:
            # In dev mode, we still need auth but the API doesn't validate the token
            # We still send it for consistency with the API endpoint requirements
            if not self.dev_mode:
                token = self._get_auth_token()
                if token:
                    headers['Authorization'] = f'Bearer {token}'
            else:
                # In dev mode, send a dummy token (API should not validate it strictly)
                headers['Authorization'] = 'Bearer dev-mode-token'

        if data:
            headers['Content-Type'] = 'application/json'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()

            # DELETE requests may return 204 No Content
            if response.status_code == 204 or not response.content:
                return {}

            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                # Resource already exists - return existing
                return e.response.json()
            raise Exception(f"HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise Exception(f"Request failed: {e}")

    # ===== Client Operations =====

    def register_client(self, client_data: Dict) -> Dict:
        """
        Register a new client.

        Args:
            client_data: Dict with id, name, subdomain, etc.

        Returns:
            Client details

        Example:
            client_data = {
                'id': 'acme-corp',
                'name': 'ACME Corporation',
                'subdomain': 'acme-corp',
                'billing_contact': 'billing@acme.com'
            }
        """
        return self._make_request('POST', 'clients', data=client_data, require_auth=True)

    def list_clients(self) -> List[Dict]:
        """List all clients"""
        return self._make_request('GET', 'clients', require_auth=False)

    def get_client(self, client_id: str) -> Dict:
        """Get client details"""
        return self._make_request('GET', f'clients/{client_id}', require_auth=False)

    def list_folders(self) -> List[Dict]:
        """List all available GCP folders under the parent folder"""
        return self._make_request('GET', 'clients/folders/list', require_auth=False)

    def update_client_folder(self, client_id: str, gcp_folder_id: str) -> Dict:
        """Update client's GCP folder"""
        return self._make_request(
            'PATCH',
            f'clients/{client_id}/folder',
            data={'gcp_folder_id': gcp_folder_id},
            require_auth=True
        )

    # ===== Project Operations =====

    def register_project(self, project_data: Dict) -> Dict:
        """
        Register a new project with environments and services.

        Args:
            project_data: Complete project configuration

        Returns:
            Project details

        Example:
            project_data = {
                'id': 'acme-corp-portal',
                'client_id': 'acme-corp',
                'name': 'Customer Portal',
                'subdomain': 'portal',
                'full_domain': 'portal.acme-corp.solvigo.ai',
                'gcp_project_id': 'acme-corp-portal',
                'github_repo': 'https://github.com/solvigo/acme-portal',
                'terraform_state_bucket': 'acme-corp-portal-tfstate',
                'project_type': 'fullstack',
                'environments': [
                    {
                        'project_id': 'acme-corp-portal',
                        'name': 'dev',
                        'database_instance': 'portal-db-dev',
                        'auto_deploy': True,
                        'requires_approval': False
                    },
                    {
                        'project_id': 'acme-corp-portal',
                        'name': 'prod',
                        'database_instance': 'portal-db-prod',
                        'auto_deploy': False,
                        'requires_approval': True
                    }
                ],
                'services': [
                    {
                        'project_id': 'acme-corp-portal',
                        'name': 'backend-dev',
                        'type': 'backend',
                        'environment': 'dev',
                        'cloud_run_service': 'backend-dev',
                        'dockerfile_path': 'backend/Dockerfile'
                    }
                ]
            }
        """
        return self._make_request('POST', 'projects', data=project_data, require_auth=True)

    def list_projects(self, client_id: Optional[str] = None, github_repo: Optional[str] = None) -> List[Dict]:
        """List all projects, optionally filtered by client or github_repo"""
        params = []
        if client_id:
            params.append(f'client_id={client_id}')
        if github_repo:
            params.append(f'github_repo={github_repo}')

        endpoint = 'projects'
        if params:
            endpoint += '?' + '&'.join(params)

        return self._make_request('GET', endpoint, require_auth=False)

    def get_project(self, project_id: str) -> Dict:
        """Get project details with environments and services"""
        return self._make_request('GET', f'projects/{project_id}', require_auth=False)

    def update_subdomain(self, project_id: str, new_subdomain: str) -> Dict:
        """Update project subdomain"""
        return self._make_request(
            'PATCH',
            f'projects/{project_id}/subdomain?new_subdomain={new_subdomain}',
            require_auth=True
        )

    def add_project_services(self, project_id: str, services: List[Dict]) -> List[Dict]:
        """
        Add services to an existing project.

        Args:
            project_id: Project ID
            services: List of service configurations

        Returns:
            List of created service records

        Example:
            services = [
                {
                    'project_id': 'acme-corp-portal',
                    'name': 'backend-dev',
                    'type': 'backend',
                    'cloud_run_service': 'backend-dev',
                    'cloud_run_region': 'europe-north1',
                    'dockerfile_path': 'backend/Dockerfile',
                    'cloudbuild_file': 'cicd/cloudbuild-backend.yaml'
                }
            ]
        """
        return self._make_request('POST', f'projects/{project_id}/services', data=services, require_auth=True)

    def bootstrap_project(self, project_id: str) -> Dict:
        """
        Bootstrap a project for Terraform.

        This enables APIs, attaches to shared VPC, and creates the Terraform state bucket
        in the client's GCP project. Called during setup wizard.

        Args:
            project_id: Project ID

        Returns:
            Dict with status, terraform_state_bucket, and apis_enabled
        """
        # Bootstrap can take longer due to API enablement and VPC attachment
        return self._make_request('POST', f'projects/{project_id}/bootstrap', require_auth=True, timeout=180)

    def list_gcp_projects(self) -> List[Dict]:
        """
        List all GCP projects accessible to the user.

        Returns:
            List of dicts with project_id, name, parent, project_number
        """
        result = self._make_request('GET', 'projects/gcp/list', require_auth=False)
        return result.get('projects', [])

    def check_gcp_project_exists(self, gcp_project_id: str) -> bool:
        """
        Check if a GCP project ID exists.

        Args:
            gcp_project_id: Project ID to check

        Returns:
            True if exists, False otherwise
        """
        try:
            result = self._make_request(
                'GET',
                f'projects/check-gcp-id/{gcp_project_id}',
                require_auth=True
            )
            return result.get('exists', False)
        except Exception:
            # If check fails, assume doesn't exist
            return False

    def setup_cicd(self, project_id: str, cicd_config: Dict) -> Dict:
        """
        Set up CI/CD for a project via Admin API.

        Creates Cloud Build triggers, service account, and artifact registry.

        Args:
            project_id: Project ID
            cicd_config: Dict with:
                - github_repo_url: str
                - environments: List[Dict] with name, pattern, cloudbuild_file, require_approval
                - services: List[Dict] with name, type, dockerfile_path

        Returns:
            Dict with status, repository, triggers, deployer_service_account, artifact_registry_repository
        """
        return self._make_request('POST', f'projects/{project_id}/cicd', data=cicd_config, require_auth=True)

    def create_build_triggers(self, project_id: str, trigger_config: Dict) -> Dict:
        """
        Create Cloud Build triggers in platform project via Admin API.

        Args:
            project_id: Project ID (e.g., "acme-portal")
            trigger_config: Trigger configuration dict with:
                - github_repo_url: GitHub repository URL
                - services: List of service configs with name, type, cloudbuild_file
                - environments: List of environment configs with name, branch_pattern/tag_pattern, require_approval

        Returns:
            Response with created triggers

        Example:
            trigger_config = {
                "github_repo_url": "https://github.com/org/repo",
                "services": [
                    {"name": "backend", "type": "backend", "cloudbuild_file": "cicd/cloudbuild-backend.yaml"}
                ],
                "environments": [
                    {"name": "dev", "branch_pattern": "^main$", "require_approval": False}
                ]
            }
        """
        return self._make_request(
            'POST',
            f'platform/projects/{project_id}/triggers',
            data=trigger_config,
            require_auth=True,
            timeout=60  # Trigger creation can take time
        )

    def get_platform_config(self) -> Dict:
        """
        Get platform configuration from Admin API.

        Returns:
            Dict with platform settings:
            - platform_project_id: Platform GCP project ID
            - github_connection: GitHub connection resource name (or None)
            - github_connection_region: Region where connection exists
            - shared_registry_location: Shared Artifact Registry location
            - shared_registry_repo: Shared Artifact Registry repository
        """
        return self._make_request(
            'GET',
            'platform/config',
            require_auth=True,
            timeout=30
        )

    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project from the registry.

        WARNING: This only removes the project from the registry database.
        It does NOT delete GCP resources.

        Args:
            project_id: Project ID to delete

        Returns:
            True if deleted successfully

        Raises:
            Exception if deletion fails
        """
        self._make_request('DELETE', f'projects/{project_id}', require_auth=True)
        return True

    # ===== Subdomain Operations (for Load Balancer) =====

    def get_all_subdomains(self) -> Dict:
        """Get all subdomain mappings (for load balancer)"""
        return self._make_request('GET', 'subdomains', require_auth=False)

    def get_subdomain_mapping(self, domain: str) -> Dict:
        """Get mapping for specific domain"""
        return self._make_request('GET', f'subdomains/{domain}', require_auth=False)

    # ===== Platform Operations =====

    def create_deployer_service_account(self, project_id: str) -> Dict:
        """
        Create per-client deployer service account in platform project.

        This service account is used by Cloud Build to deploy to the client project.

        Args:
            project_id: Client project ID (from registry)

        Returns:
            Dict with deployer_sa_email and permissions granted
        """
        return self._make_request(
            'POST',
            f'platform/projects/{project_id}/deployer-sa',
            require_auth=True
        )

    def setup_vpc_peering(self, project_id: str, vpc_config: Dict) -> Dict:
        """
        Set up VPC peering for client project to shared VPC.

        Args:
            project_id: Client project ID
            vpc_config: Dict with client_project_id, region

        Returns:
            Dict with VPC peering status
        """
        return self._make_request(
            'POST',
            f'platform/projects/{project_id}/vpc-peering',
            data=vpc_config,
            require_auth=True
        )

    def create_artifact_registry(self, project_id: str) -> Dict:
        """
        Create/configure Artifact Registry access for client project.

        Args:
            project_id: Client project ID

        Returns:
            Dict with registry_url
        """
        return self._make_request(
            'POST',
            f'platform/projects/{project_id}/artifact-registry',
            require_auth=True
        )

    def create_build_triggers(self, project_id: str, trigger_config: Dict) -> Dict:
        """
        Create Cloud Build triggers in platform project.

        Args:
            project_id: Client project ID
            trigger_config: Dict with github_repo_url and environments[]

        Returns:
            Dict with created trigger IDs and names

        Example:
            trigger_config = {
                'github_repo_url': 'https://github.com/org/repo',
                'environments': [
                    {
                        'name': 'staging',
                        'branch_pattern': 'main',
                        'cloudbuild_file': 'cicd/cloudbuild-backend.yaml',
                        'require_approval': False
                    },
                    {
                        'name': 'prod',
                        'tag_pattern': 'v*',
                        'cloudbuild_file': 'cicd/cloudbuild-backend.yaml',
                        'require_approval': True
                    }
                ]
            }
        """
        return self._make_request(
            'POST',
            f'platform/projects/{project_id}/triggers',
            data=trigger_config,
            require_auth=True
        )

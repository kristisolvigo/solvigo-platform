"""
Registry API client for CLI to register and query projects
"""
import os
import requests
from typing import Dict, List, Optional
from rich.console import Console

console = Console()


class RegistryClient:
    """Client for interacting with Solvigo Registry API"""

    def __init__(self):
        self.api_url = os.getenv(
            'SOLVIGO_REGISTRY_URL',
            'https://registry-api-430162142300.europe-north1.run.app'
        )
        self.base_url = f"{self.api_url}/api/v1"
        self._token = None

    def _get_auth_token(self) -> str:
        """Get GCP ID token for authenticating to Cloud Run"""
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

    def _make_request(self, method: str, endpoint: str, data: Dict = None, require_auth: bool = True) -> Dict:
        """Make HTTP request to registry API"""
        url = f"{self.base_url}/{endpoint}"
        headers = {}

        if require_auth:
            token = self._get_auth_token()
            headers['Authorization'] = f'Bearer {token}'

        if data:
            headers['Content-Type'] = 'application/json'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
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
                'terraform_state_bucket': 'acme-corp-terraform-state',
                'project_type': 'fullstack',
                'environments': [
                    {
                        'project_id': 'acme-corp-portal',
                        'name': 'staging',
                        'database_instance': 'portal-db-staging',
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
                        'name': 'backend-staging',
                        'type': 'backend',
                        'environment': 'staging',
                        'cloud_run_service': 'backend-staging',
                        'dockerfile_path': 'backend/Dockerfile'
                    }
                ]
            }
        """
        return self._make_request('POST', 'projects', data=project_data, require_auth=True)

    def list_projects(self, client_id: Optional[str] = None) -> List[Dict]:
        """List all projects, optionally filtered by client"""
        endpoint = f'projects?client_id={client_id}' if client_id else 'projects'
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

    # ===== Subdomain Operations (for Load Balancer) =====

    def get_all_subdomains(self) -> Dict:
        """Get all subdomain mappings (for load balancer)"""
        return self._make_request('GET', 'subdomains', require_auth=False)

    def get_subdomain_mapping(self, domain: str) -> Dict:
        """Get mapping for specific domain"""
        return self._make_request('GET', f'subdomains/{domain}', require_auth=False)

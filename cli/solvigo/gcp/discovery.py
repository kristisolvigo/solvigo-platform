"""
GCP Resource Discovery - scan projects for existing resources
"""
import subprocess
import json
from typing import Dict, List, Optional
from rich.console import Console
from rich.progress import Progress

console = Console()


class ResourceDiscovery:
    """Discovers resources in a GCP project"""

    def __init__(self, project_id: str):
        self.project_id = project_id

    def discover_all(self) -> Dict[str, List[Dict]]:
        """
        Discover all supported resources in the project.

        Returns:
            dict: Resource types mapped to list of resources
        """
        console.print(f"\n🔍 Scanning GCP project: [cyan]{self.project_id}[/cyan]...")

        resources = {}

        # Note: We wrap each discovery in try/except to handle timeouts gracefully
        # If an API isn't enabled, gcloud will prompt for confirmation which causes timeout

        with Progress() as progress:
            task = progress.add_task("[cyan]Discovering resources...", total=8)

            # Cloud Run services
            try:
                resources['cloud_run'] = self.discover_cloud_run()
            except Exception as e:
                console.print(f"[dim]Skipping Cloud Run (API may not be enabled)[/dim]")
                resources['cloud_run'] = []
            progress.advance(task)

            # Cloud SQL instances
            try:
                resources['cloud_sql'] = self.discover_cloud_sql()
            except Exception as e:
                console.print(f"[dim]Skipping Cloud SQL (API may not be enabled)[/dim]")
                resources['cloud_sql'] = []
            progress.advance(task)

            # Firestore
            try:
                resources['firestore'] = self.discover_firestore()
            except Exception as e:
                resources['firestore'] = []
            progress.advance(task)

            # Storage buckets
            try:
                resources['storage'] = self.discover_storage_buckets()
            except Exception as e:
                console.print(f"[dim]Skipping Storage (API may not be enabled)[/dim]")
                resources['storage'] = []
            progress.advance(task)

            # Secrets
            try:
                resources['secrets'] = self.discover_secrets()
            except Exception as e:
                console.print(f"[dim]Skipping Secrets (API may not be enabled)[/dim]")
                resources['secrets'] = []
            progress.advance(task)

            # Service accounts
            try:
                resources['service_accounts'] = self.discover_service_accounts()
            except Exception as e:
                resources['service_accounts'] = []
            progress.advance(task)

            # VPC connectors
            try:
                resources['vpc_connectors'] = self.discover_vpc_connectors()
            except Exception as e:
                resources['vpc_connectors'] = []
            progress.advance(task)

            # Enabled APIs
            try:
                resources['apis'] = self.discover_enabled_apis()
            except Exception as e:
                resources['apis'] = []
            progress.advance(task)

        # Print summary
        self._print_discovery_summary(resources)

        return resources

    def discover_cloud_run(self) -> List[Dict]:
        """Discover Cloud Run services"""
        try:
            result = subprocess.run(
                [
                    'gcloud', 'run', 'services', 'list',
                    f'--project={self.project_id}',
                    '--format=json',
                    '--verbosity=error'  # Suppress prompts
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=10  # 10 second timeout (faster failure)
            )

            # Check if command failed
            if result.returncode != 0:
                # API might not be enabled, just return empty
                return []

            services = json.loads(result.stdout) if result.stdout else []

            # Enhance with metadata
            enhanced = []
            for service in services:
                enhanced.append({
                    'name': service.get('metadata', {}).get('name'),
                    'region': service.get('metadata', {}).get('labels', {}).get('cloud.googleapis.com/location'),
                    'url': service.get('status', {}).get('url'),
                    'image': service.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [{}])[0].get('image'),
                    'type': self._classify_cloud_run_service(service),
                    'raw': service
                })

            return enhanced

        except subprocess.CalledProcessError:
            return []
        except json.JSONDecodeError:
            return []

    def discover_cloud_sql(self) -> List[Dict]:
        """Discover Cloud SQL instances"""
        try:
            result = subprocess.run(
                [
                    'gcloud', 'sql', 'instances', 'list',
                    f'--project={self.project_id}',
                    '--format=json',
                    '--verbosity=error'
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )

            if result.returncode != 0:
                return []

            instances = json.loads(result.stdout) if result.stdout else []

            enhanced = []
            for instance in instances:
                enhanced.append({
                    'name': instance.get('name'),
                    'database_version': instance.get('databaseVersion'),
                    'tier': instance.get('settings', {}).get('tier'),
                    'region': instance.get('region'),
                    'state': instance.get('state'),
                    'raw': instance
                })

            return enhanced

        except subprocess.TimeoutExpired:
            console.print("[yellow]⚠ Cloud SQL discovery timed out[/yellow]")
            return []
        except subprocess.CalledProcessError:
            return []
        except json.JSONDecodeError:
            return []
        except Exception as e:
            console.print(f"[yellow]⚠ Error discovering Cloud SQL: {e}[/yellow]")
            return []

    def discover_firestore(self) -> List[Dict]:
        """Check if Firestore is enabled"""
        try:
            result = subprocess.run(
                [
                    'gcloud', 'firestore', 'databases', 'list',
                    f'--project={self.project_id}',
                    '--format=json',
                    '--verbosity=error'
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )

            if result.returncode == 0 and result.stdout:
                databases = json.loads(result.stdout)
                return [{'name': db.get('name'), 'type': 'firestore', 'raw': db} for db in databases]

            return []

        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return []

    def discover_storage_buckets(self) -> List[Dict]:
        """Discover Cloud Storage buckets"""
        try:
            result = subprocess.run(
                [
                    'gcloud', 'storage', 'buckets', 'list',
                    f'--project={self.project_id}',
                    '--format=json',
                    '--verbosity=error'
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )

            if result.returncode != 0:
                return []

            buckets = json.loads(result.stdout) if result.stdout else []

            enhanced = []
            for bucket in buckets:
                name = bucket.get('name', '')
                enhanced.append({
                    'name': name,
                    'location': bucket.get('location'),
                    'storage_class': bucket.get('storageClass'),
                    'is_terraform_state': 'terraform-state' in name,
                    'raw': bucket
                })

            return enhanced

        except subprocess.TimeoutExpired:
            console.print("[yellow]⚠ Storage discovery timed out[/yellow]")
            return []
        except subprocess.CalledProcessError:
            return []
        except json.JSONDecodeError:
            return []
        except Exception as e:
            console.print(f"[yellow]⚠ Error discovering storage: {e}[/yellow]")
            return []

    def discover_secrets(self) -> List[Dict]:
        """Discover Secret Manager secrets"""
        try:
            result = subprocess.run(
                [
                    'gcloud', 'secrets', 'list',
                    f'--project={self.project_id}',
                    '--format=json',
                    '--verbosity=error'
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )

            if result.returncode != 0:
                return []

            secrets = json.loads(result.stdout) if result.stdout else []

            enhanced = []
            for secret in secrets:
                enhanced.append({
                    'name': secret.get('name').split('/')[-1],  # Extract name from full path
                    'created': secret.get('createTime'),
                    'raw': secret
                })

            return enhanced

        except subprocess.TimeoutExpired:
            console.print("[yellow]⚠ Secrets discovery timed out[/yellow]")
            return []
        except subprocess.CalledProcessError:
            return []
        except json.JSONDecodeError:
            return []
        except Exception as e:
            console.print(f"[yellow]⚠ Error discovering secrets: {e}[/yellow]")
            return []

    def discover_service_accounts(self) -> List[Dict]:
        """Discover service accounts"""
        try:
            result = subprocess.run(
                [
                    'gcloud', 'iam', 'service-accounts', 'list',
                    f'--project={self.project_id}',
                    '--format=json',
                    '--verbosity=error'
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )

            if result.returncode != 0:
                return []

            accounts = json.loads(result.stdout) if result.stdout else []

            # Filter out default GCP service accounts
            filtered = []
            for account in accounts:
                email = account.get('email', '')
                # Skip default accounts
                if not any(skip in email for skip in ['@cloudservices', '@compute-system', '@gcp-sa-']):
                    filtered.append({
                        'email': email,
                        'display_name': account.get('displayName'),
                        'raw': account
                    })

            return filtered

        except subprocess.TimeoutExpired:
            console.print("[yellow]⚠ Service accounts discovery timed out[/yellow]")
            return []
        except subprocess.CalledProcessError:
            return []
        except json.JSONDecodeError:
            return []
        except Exception as e:
            console.print(f"[yellow]⚠ Error discovering service accounts: {e}[/yellow]")
            return []

    def discover_vpc_connectors(self) -> List[Dict]:
        """Discover VPC Access connectors"""
        try:
            result = subprocess.run(
                [
                    'gcloud', 'compute', 'networks', 'vpc-access', 'connectors', 'list',
                    f'--project={self.project_id}',
                    '--format=json',
                    '--verbosity=error'
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )

            if result.returncode == 0 and result.stdout:
                connectors = json.loads(result.stdout)
                return [{'name': c.get('name'), 'region': c.get('region'), 'raw': c} for c in connectors]

            return []

        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return []

    def discover_enabled_apis(self) -> List[Dict]:
        """Discover enabled GCP APIs"""
        try:
            result = subprocess.run(
                [
                    'gcloud', 'services', 'list',
                    '--enabled',
                    f'--project={self.project_id}',
                    '--format=json',
                    '--verbosity=error'
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )

            if result.returncode != 0:
                return []

            services = json.loads(result.stdout) if result.stdout else []

            # Filter to interesting APIs
            interesting_apis = {
                'aiplatform.googleapis.com': 'Vertex AI',
                'bigquery.googleapis.com': 'BigQuery',
                'pubsub.googleapis.com': 'Pub/Sub',
                'translate.googleapis.com': 'Translation API',
                'vision.googleapis.com': 'Vision API',
                'language.googleapis.com': 'Natural Language API',
                'cloudtasks.googleapis.com': 'Cloud Tasks',
                'cloudscheduler.googleapis.com': 'Cloud Scheduler',
            }

            filtered = []
            for service in services:
                name = service.get('config', {}).get('name', '')
                if name in interesting_apis:
                    filtered.append({
                        'name': name,
                        'title': interesting_apis[name],
                        'raw': service
                    })

            return filtered

        except subprocess.TimeoutExpired:
            console.print("[yellow]⚠ API discovery timed out[/yellow]")
            return []
        except subprocess.CalledProcessError:
            return []
        except json.JSONDecodeError:
            return []
        except Exception as e:
            console.print(f"[yellow]⚠ Error discovering APIs: {e}[/yellow]")
            return []

    def _classify_cloud_run_service(self, service: Dict) -> str:
        """
        Classify a Cloud Run service as frontend, backend, or unknown.

        Args:
            service: Raw Cloud Run service object

        Returns:
            'frontend', 'backend', or 'unknown'
        """
        # Get environment variables
        containers = service.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
        if not containers:
            return 'unknown'

        env_vars = containers[0].get('env', [])
        env_names = [env.get('name', '') for env in env_vars]

        # Frontend indicators
        frontend_indicators = ['REACT_APP_', 'VITE_', 'NEXT_PUBLIC_', 'VUE_APP_']
        # Backend indicators
        backend_indicators = ['DATABASE_URL', 'REDIS_URL', 'SQLALCHEMY', 'DJANGO_SETTINGS', 'FASTAPI']

        frontend_score = sum(1 for env in env_names if any(ind in env for ind in frontend_indicators))
        backend_score = sum(1 for env in env_names if any(ind in env for ind in backend_indicators))

        if frontend_score > backend_score:
            return 'frontend'
        elif backend_score > frontend_score:
            return 'backend'
        else:
            return 'unknown'

    def _print_discovery_summary(self, resources: Dict[str, List]):
        """Print a summary of discovered resources"""
        console.print()

        summaries = []
        if resources.get('cloud_run'):
            summaries.append(f"✓ Found Cloud Run services ({len(resources['cloud_run'])})")
        if resources.get('cloud_sql'):
            summaries.append(f"✓ Found Cloud SQL instances ({len(resources['cloud_sql'])})")
        if resources.get('firestore'):
            summaries.append(f"✓ Found Firestore database")
        if resources.get('storage'):
            summaries.append(f"✓ Found Storage buckets ({len(resources['storage'])})")
        if resources.get('secrets'):
            summaries.append(f"✓ Found Secrets ({len(resources['secrets'])})")
        if resources.get('service_accounts'):
            summaries.append(f"✓ Found Service Accounts ({len(resources['service_accounts'])})")
        if resources.get('vpc_connectors'):
            summaries.append(f"✓ Found VPC connectors ({len(resources['vpc_connectors'])})")
        if resources.get('apis'):
            summaries.append(f"✓ Found enabled APIs ({len(resources['apis'])})")

        for summary in summaries:
            console.print(summary)

        console.print()


def list_accessible_projects() -> List[Dict[str, str]]:
    """
    List all GCP projects the user has access to.

    Returns:
        List of dicts with project_id, name, and parent info
    """
    try:
        result = subprocess.run(
            [
                'gcloud', 'projects', 'list',
                '--format=json'
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30
        )

        if result.returncode != 0:
            return []

        projects = json.loads(result.stdout) if result.stdout else []

        # Extract relevant info
        project_list = []
        for project in projects:
            project_list.append({
                'project_id': project.get('projectId'),
                'name': project.get('name'),
                'number': project.get('projectNumber'),
                'state': project.get('lifecycleState'),
                'parent': project.get('parent', {})
            })

        return project_list

    except subprocess.TimeoutExpired:
        console.print("[yellow]⚠ Project listing timed out[/yellow]")
        return []
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []
    except Exception as e:
        console.print(f"[yellow]⚠ Error listing projects: {e}[/yellow]")
        return []


def verify_gcp_project_access(project_id: str) -> bool:
    """
    Verify that we have access to the GCP project.

    Args:
        project_id: GCP project ID

    Returns:
        True if accessible, False otherwise
    """
    try:
        result = subprocess.run(
            ['gcloud', 'projects', 'describe', project_id],
            capture_output=True,
            text=True,
            check=True
        )
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

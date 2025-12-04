"""
Platform operations endpoints - handles cross-project resources
managed in the platform project (solvigo-platform-prod)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
import logging

from google.cloud import iam_admin_v1
from google.cloud import resourcemanager_v3
from google.cloud import compute_v1
from google.cloud import service_usage_v1
from google.cloud import artifactregistry_v1
from google.cloud.devtools import cloudbuild_v1
from google.api_core import exceptions as google_exceptions
import time
import re

from app.database import get_db
from app.auth import get_current_user
from app import models, schemas
from app.gcp.errors import handle_gcp_error

logger = logging.getLogger(__name__)
router = APIRouter()

# Platform project configuration
PLATFORM_PROJECT_ID = "solvigo-platform-prod"
PLATFORM_PROJECT_NUMBER = "430162142300"  # Update if needed
SHARED_REGISTRY_LOCATION = "europe-north1"
SHARED_REGISTRY_REPO = "solvigo-apps"
GITHUB_CONNECTION_REGION = "europe-north2"
GITHUB_CONNECTION_NAME = "solvigo-github-connection"


@router.get("/config", status_code=200)
def get_platform_config(
    current_user: str = Depends(get_current_user)
):
    """
    Get platform configuration including GitHub connection.

    Returns platform-level settings that clients need for infrastructure setup.
    """
    from google.cloud.devtools import cloudbuild_v2
    from app.gcp.credentials import get_credentials
    import os

    try:
        # Get credentials (uses ADC or impersonation based on environment)
        credentials, project = get_credentials()

        # In dev mode, using service account key
        dev_mode = os.getenv('DEV_MODE', 'false').lower() == 'true'
        if dev_mode:
            logger.info("Running in dev mode - using service account key")

        # Search for GitHub connection in known regions
        regions = ['europe-north2', 'europe-north1', 'europe-west1', 'us-central1']

        client = cloudbuild_v2.RepositoryManagerClient(credentials=credentials)

        for region in regions:
            try:
                parent = f"projects/{PLATFORM_PROJECT_ID}/locations/{region}"
                request = cloudbuild_v2.ListConnectionsRequest(parent=parent)
                logger.info(f"Searching for connections in region {region}")
                connections = client.list_connections(request=request)

                # Find first GitHub connection
                connection_count = 0
                for connection in connections:
                    connection_count += 1
                    logger.info(f"Found connection: {connection.name} in region {region}")
                    return {
                        'platform_project_id': PLATFORM_PROJECT_ID,
                        'github_connection': connection.name,
                        'github_connection_region': region,
                        'shared_registry_location': SHARED_REGISTRY_LOCATION,
                        'shared_registry_repo': SHARED_REGISTRY_REPO
                    }

                logger.info(f"No connections found in region {region} (searched successfully)")
            except Exception as e:
                logger.warning(f"Error searching connections in region {region}: {e}")
                continue

        # No connection found
        logger.warning("No GitHub connection found in any region")
        return {
            'platform_project_id': PLATFORM_PROJECT_ID,
            'github_connection': None,
            'shared_registry_location': SHARED_REGISTRY_LOCATION,
            'shared_registry_repo': SHARED_REGISTRY_REPO
        }

    except Exception as e:
        logger.error(f"Failed to fetch platform config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch platform configuration: {str(e)}"
        )


@router.post("/projects/{project_id}/deployer-sa", status_code=201)
def create_deployer_service_account(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Create per-client deployer service account in platform project.

    This SA is used by Cloud Build to deploy to the client project.

    Args:
        project_id: Client project ID (from registry)

    Returns:
        Dict with service account email and permissions granted
    """
    # Verify project exists
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    client = db.query(models.Client).filter(models.Client.id == project.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    client_slug = client.id
    deployer_sa_name = f"{client_slug}-deployer"
    deployer_email = f"{deployer_sa_name}@{PLATFORM_PROJECT_ID}.iam.gserviceaccount.com"

    permissions_granted = []

    try:
        # Initialize IAM client
        iam_client = iam_admin_v1.IAMClient()
        project_name = f"projects/{PLATFORM_PROJECT_ID}"

        # Step 1: Create service account in platform project
        logger.info(f"Creating deployer SA: {deployer_email}")
        try:
            service_account = iam_client.create_service_account(
                request={
                    "name": project_name,
                    "account_id": deployer_sa_name,
                    "service_account": {
                        "display_name": f"Deployer for {client.name}",
                        "description": f"Service account for deploying {client.name} services via Cloud Build"
                    }
                }
            )
            logger.info(f"Created service account: {service_account.email}")
        except google_exceptions.AlreadyExists:
            logger.info(f"Service account already exists: {deployer_email}")
            # Get existing service account
            sa_resource_name = f"{project_name}/serviceAccounts/{deployer_email}"
            service_account = iam_client.get_service_account(name=sa_resource_name)

        # Step 2: Grant permissions on client project
        if project.gcp_project_id:
            try:
                projects_client = resourcemanager_v3.ProjectsClient()
                client_project_name = f"projects/{project.gcp_project_id}"

                # Grant roles/run.admin on client project
                logger.info(f"Granting roles/run.admin on {project.gcp_project_id}")
                policy = projects_client.get_iam_policy(resource=client_project_name)

                # Add binding for run.admin
                run_admin_binding = None
                for binding in policy.bindings:
                    if binding.role == "roles/run.admin":
                        run_admin_binding = binding
                        break

                if not run_admin_binding:
                    from google.iam.v1 import policy_pb2
                    run_admin_binding = policy_pb2.Binding(role="roles/run.admin")
                    policy.bindings.append(run_admin_binding)

                member_str = f"serviceAccount:{deployer_email}"
                if member_str not in run_admin_binding.members:
                    run_admin_binding.members.append(member_str)
                    projects_client.set_iam_policy(resource=client_project_name, policy=policy)
                    permissions_granted.append(f"roles/run.admin on {project.gcp_project_id}")
                    logger.info(f"Granted roles/run.admin")
                else:
                    logger.info(f"roles/run.admin already granted")
                    permissions_granted.append(f"roles/run.admin on {project.gcp_project_id} (existing)")

                # Grant roles/secretmanager.secretAccessor on client project
                logger.info(f"Granting roles/secretmanager.secretAccessor on {project.gcp_project_id}")
                policy = projects_client.get_iam_policy(resource=client_project_name)

                secret_accessor_binding = None
                for binding in policy.bindings:
                    if binding.role == "roles/secretmanager.secretAccessor":
                        secret_accessor_binding = binding
                        break

                if not secret_accessor_binding:
                    from google.iam.v1 import policy_pb2
                    secret_accessor_binding = policy_pb2.Binding(role="roles/secretmanager.secretAccessor")
                    policy.bindings.append(secret_accessor_binding)

                if member_str not in secret_accessor_binding.members:
                    secret_accessor_binding.members.append(member_str)
                    projects_client.set_iam_policy(resource=client_project_name, policy=policy)
                    permissions_granted.append(f"roles/secretmanager.secretAccessor on {project.gcp_project_id}")
                    logger.info(f"Granted roles/secretmanager.secretAccessor")
                else:
                    logger.info(f"roles/secretmanager.secretAccessor already granted")
                    permissions_granted.append(f"roles/secretmanager.secretAccessor on {project.gcp_project_id} (existing)")

            except Exception as e:
                logger.error(f"Failed to grant client project permissions: {e}")
                raise handle_gcp_error(e, "Grant client project permissions", project.gcp_project_id)

        # Step 3: Grant Cloud Build SA permission to impersonate deployer SA
        logger.info(f"Granting Cloud Build SA permission to impersonate {deployer_email}")
        try:
            sa_resource_name = f"{project_name}/serviceAccounts/{deployer_email}"
            sa_policy = iam_client.get_iam_policy(resource=sa_resource_name)

            cloudbuild_sa = f"serviceAccount:{PLATFORM_PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

            # Add iam.serviceAccountUser role for Cloud Build SA
            user_binding = None
            for binding in sa_policy.bindings:
                if binding.role == "roles/iam.serviceAccountUser":
                    user_binding = binding
                    break

            if not user_binding:
                from google.iam.v1 import policy_pb2
                user_binding = policy_pb2.Binding(role="roles/iam.serviceAccountUser")
                sa_policy.bindings.append(user_binding)

            if cloudbuild_sa not in user_binding.members:
                user_binding.members.append(cloudbuild_sa)
                iam_client.set_iam_policy(resource=sa_resource_name, policy=sa_policy)
                permissions_granted.append(f"Cloud Build SA can impersonate {deployer_email}")
                logger.info("Granted impersonation permission to Cloud Build SA")
            else:
                logger.info("Cloud Build SA already has impersonation permission")
                permissions_granted.append(f"Cloud Build SA can impersonate {deployer_email} (existing)")

        except Exception as e:
            logger.error(f"Failed to grant impersonation permission: {e}")
            raise handle_gcp_error(e, "Grant impersonation permission", deployer_email)

        # Log in audit trail
        db.add(models.AuditLog(
            user_email=current_user,
            action='create_deployer_sa',
            entity_type='project',
            entity_id=project_id,
            new_value={
                'deployer_sa': deployer_email,
                'permissions': permissions_granted
            }
        ))
        db.commit()

        return {
            'status': 'created',
            'deployer_sa_email': deployer_email,
            'permissions': permissions_granted
        }

    except HTTPException:
        # Re-raise HTTP exceptions from handle_gcp_error
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating deployer SA: {e}")
        db.rollback()
        raise handle_gcp_error(e, "Create deployer service account", deployer_email)


@router.post("/projects/{project_id}/vpc-peering", status_code=201)
def setup_vpc_peering(
    project_id: str,
    vpc_config: schemas.VPCConfig,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Set up VPC peering/attachment for client project to shared VPC.

    Args:
        project_id: Client project ID
        vpc_config: VPC configuration (client_project_id, region)

    Returns:
        Dict with peering status
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    client_project_id = vpc_config.client_project_id
    region = vpc_config.region

    try:
        # Step 1: Enable Compute API in client project
        logger.info(f"Enabling Compute API in {client_project_id}")
        try:
            service_usage_client = service_usage_v1.ServiceUsageClient()
            service_name = f"projects/{client_project_id}/services/compute.googleapis.com"

            try:
                # Check if already enabled
                service = service_usage_client.get_service(name=service_name)
                if service.state == service_usage_v1.State.ENABLED:
                    logger.info("Compute API already enabled")
                else:
                    # Enable the service
                    operation = service_usage_client.enable_service(name=service_name)
                    logger.info("Waiting for Compute API enablement (may take up to 2 minutes)...")
                    # Wait for operation to complete (with timeout)
                    start_time = time.time()
                    while not operation.done() and (time.time() - start_time) < 120:
                        time.sleep(5)
                        operation.reload()

                    if not operation.done():
                        logger.warning("API enablement may still be in progress")
                    else:
                        logger.info("Compute API enabled successfully")
            except google_exceptions.NotFound:
                # Service not found, try to enable it
                operation = service_usage_client.enable_service(name=service_name)
                logger.info("Enabling Compute API...")
                time.sleep(10)  # Give it some time

        except Exception as e:
            logger.error(f"Failed to enable Compute API: {e}")
            raise handle_gcp_error(e, "Enable Compute API", client_project_id)

        # Step 2: Attach client project to shared VPC
        logger.info(f"Attaching {client_project_id} to shared VPC in {PLATFORM_PROJECT_ID}")
        try:
            projects_client = compute_v1.ProjectsClient()

            # Enable XPN (shared VPC) resource - associate client project with host
            xpn_resource = compute_v1.ProjectsEnableXpnResourceRequest()
            xpn_resource_body = compute_v1.ProjectsEnableXpnResourceRequest()
            xpn_resource_body.xpn_resource = compute_v1.XpnResourceId()
            xpn_resource_body.xpn_resource.id = client_project_id
            xpn_resource_body.xpn_resource.type_ = "PROJECT"

            try:
                operation = projects_client.enable_xpn_resource(
                    project=PLATFORM_PROJECT_ID,
                    projects_enable_xpn_resource_request_resource=xpn_resource_body
                )
                # Wait for operation
                logger.info("Waiting for shared VPC attachment...")
                start_time = time.time()
                while not operation.done() and (time.time() - start_time) < 60:
                    time.sleep(3)

                if operation.done():
                    logger.info(f"Successfully attached {client_project_id} to shared VPC")
                else:
                    logger.warning("Shared VPC attachment may still be in progress")
            except google_exceptions.AlreadyExists:
                logger.info(f"Project already attached to shared VPC")
            except google_exceptions.FailedPrecondition as e:
                # May already be associated
                logger.info(f"Shared VPC association status unclear: {e}")

        except Exception as e:
            logger.error(f"Failed to attach to shared VPC: {e}")
            raise handle_gcp_error(e, "Attach to shared VPC", client_project_id)

        # Step 3: Grant network user permissions to deployer SA
        logger.info(f"Granting network user permissions")
        try:
            client = db.query(models.Client).filter(models.Client.id == project.client_id).first()
            deployer_email = f"{client.id}-deployer@{PLATFORM_PROJECT_ID}.iam.gserviceaccount.com"

            projects_client_rm = resourcemanager_v3.ProjectsClient()
            platform_project_name = f"projects/{PLATFORM_PROJECT_ID}"

            # Grant compute.networkUser role on platform project
            policy = projects_client_rm.get_iam_policy(resource=platform_project_name)

            network_user_binding = None
            for binding in policy.bindings:
                if binding.role == "roles/compute.networkUser":
                    network_user_binding = binding
                    break

            if not network_user_binding:
                from google.iam.v1 import policy_pb2
                network_user_binding = policy_pb2.Binding(role="roles/compute.networkUser")
                policy.bindings.append(network_user_binding)

            member_str = f"serviceAccount:{deployer_email}"
            if member_str not in network_user_binding.members:
                network_user_binding.members.append(member_str)
                projects_client_rm.set_iam_policy(resource=platform_project_name, policy=policy)
                logger.info(f"Granted roles/compute.networkUser to {deployer_email}")
            else:
                logger.info(f"roles/compute.networkUser already granted")

        except Exception as e:
            logger.warning(f"Failed to grant network user permissions (non-critical): {e}")

        # Log in audit trail
        db.add(models.AuditLog(
            user_email=current_user,
            action='setup_vpc_peering',
            entity_type='project',
            entity_id=project_id,
            new_value={
                'host_project': PLATFORM_PROJECT_ID,
                'client_project': client_project_id,
                'region': region
            }
        ))
        db.commit()

        return {
            'status': 'configured',
            'host_project': PLATFORM_PROJECT_ID,
            'client_project': client_project_id,
            'region': region,
            'shared_vpc_network': f"projects/{PLATFORM_PROJECT_ID}/global/networks/default"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error setting up VPC: {e}")
        db.rollback()
        raise handle_gcp_error(e, "Setup VPC peering", client_project_id)


@router.post("/projects/{project_id}/artifact-registry", status_code=201)
def create_artifact_registry(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Create/configure Artifact Registry repository access in platform project.

    Uses shared registry: europe-north1-docker.pkg.dev/solvigo-platform-prod/solvigo-apps

    Args:
        project_id: Client project ID

    Returns:
        Dict with repository URL
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    client = db.query(models.Client).filter(models.Client.id == project.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    registry_url = f"{SHARED_REGISTRY_LOCATION}-docker.pkg.dev/{PLATFORM_PROJECT_ID}/{SHARED_REGISTRY_REPO}"
    deployer_email = f"{client.id}-deployer@{PLATFORM_PROJECT_ID}.iam.gserviceaccount.com"
    cloudbuild_sa = f"{PLATFORM_PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

    permissions_granted = []

    try:
        # Initialize Artifact Registry client
        ar_client = artifactregistry_v1.ArtifactRegistryClient()
        repository_name = f"projects/{PLATFORM_PROJECT_ID}/locations/{SHARED_REGISTRY_LOCATION}/repositories/{SHARED_REGISTRY_REPO}"

        # Step 1: Verify repository exists
        logger.info(f"Verifying Artifact Registry repository: {repository_name}")
        try:
            repository = ar_client.get_repository(name=repository_name)
            logger.info(f"Repository exists: {repository.name}")
        except google_exceptions.NotFound:
            raise HTTPException(
                status_code=404,
                detail=f"Shared Artifact Registry repository not found: {SHARED_REGISTRY_REPO}"
            )

        # Step 2: Grant permissions to deployer SA
        logger.info(f"Granting Artifact Registry permissions to {deployer_email}")
        try:
            # Get current IAM policy
            policy = ar_client.get_iam_policy(resource=repository_name)

            # Grant artifactregistry.writer role to deployer SA
            writer_binding = None
            for binding in policy.bindings:
                if binding.role == "roles/artifactregistry.writer":
                    writer_binding = binding
                    break

            if not writer_binding:
                from google.iam.v1 import policy_pb2
                writer_binding = policy_pb2.Binding(role="roles/artifactregistry.writer")
                policy.bindings.append(writer_binding)

            deployer_member = f"serviceAccount:{deployer_email}"
            if deployer_member not in writer_binding.members:
                writer_binding.members.append(deployer_member)
                ar_client.set_iam_policy(resource=repository_name, policy=policy)
                permissions_granted.append(f"roles/artifactregistry.writer for {deployer_email}")
                logger.info(f"Granted artifactregistry.writer to deployer SA")
            else:
                logger.info(f"Deployer SA already has artifactregistry.writer")
                permissions_granted.append(f"roles/artifactregistry.writer for {deployer_email} (existing)")

        except Exception as e:
            logger.error(f"Failed to grant deployer SA permissions: {e}")
            raise handle_gcp_error(e, "Grant Artifact Registry permissions to deployer SA", deployer_email)

        # Step 3: Grant permissions to Cloud Build SA
        logger.info(f"Granting Artifact Registry permissions to Cloud Build SA")
        try:
            # Refresh policy
            policy = ar_client.get_iam_policy(resource=repository_name)

            # Grant artifactregistry.writer role to Cloud Build SA
            writer_binding = None
            for binding in policy.bindings:
                if binding.role == "roles/artifactregistry.writer":
                    writer_binding = binding
                    break

            cloudbuild_member = f"serviceAccount:{cloudbuild_sa}"
            if cloudbuild_member not in writer_binding.members:
                writer_binding.members.append(cloudbuild_member)
                ar_client.set_iam_policy(resource=repository_name, policy=policy)
                permissions_granted.append(f"roles/artifactregistry.writer for Cloud Build SA")
                logger.info(f"Granted artifactregistry.writer to Cloud Build SA")
            else:
                logger.info(f"Cloud Build SA already has artifactregistry.writer")
                permissions_granted.append(f"roles/artifactregistry.writer for Cloud Build SA (existing)")

        except Exception as e:
            logger.error(f"Failed to grant Cloud Build SA permissions: {e}")
            raise handle_gcp_error(e, "Grant Artifact Registry permissions to Cloud Build SA", cloudbuild_sa)

        # Log in audit trail
        db.add(models.AuditLog(
            user_email=current_user,
            action='create_artifact_registry',
            entity_type='project',
            entity_id=project_id,
            new_value={
                'registry_url': registry_url,
                'permissions': permissions_granted
            }
        ))
        db.commit()

        return {
            'status': 'configured',
            'registry_url': registry_url,
            'permissions': permissions_granted
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error configuring Artifact Registry: {e}")
        db.rollback()
        raise handle_gcp_error(e, "Configure Artifact Registry", registry_url)


def parse_github_url(github_url: str) -> tuple:
    """
    Parse GitHub URL to extract owner and repo name.

    Examples:
        https://github.com/owner/repo → ("owner", "repo")
        https://github.com/owner/repo.git → ("owner", "repo")
        git@github.com:owner/repo.git → ("owner", "repo")

    Args:
        github_url: GitHub repository URL

    Returns:
        Tuple of (owner, repo_name)

    Raises:
        ValueError: If URL format is invalid
    """
    import re
    pattern = r'github\.com[:/]([^/]+)/([^/.]+)'
    match = re.search(pattern, github_url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {github_url}")
    return match.group(1), match.group(2).replace('.git', '')


@router.post("/projects/{project_id}/triggers", status_code=201)
def create_build_triggers(
    project_id: str,
    trigger_config: schemas.EnhancedTriggerConfig,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Create Cloud Build triggers in platform project.

    Creates one trigger per service per environment.
    Example: backend + frontend with dev + prod = 4 triggers

    Args:
        project_id: Client project ID
        trigger_config: Enhanced trigger configuration with services and environments

    Returns:
        Dict with created trigger IDs and names
    """
    # Verify project exists
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    client = db.query(models.Client).filter(models.Client.id == project.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Parse GitHub repo URL
    try:
        repo_owner, repo_name = parse_github_url(trigger_config.github_repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Deployer SA now lives in client project (not platform project)
    deployer_email = f"deployer@{project.gcp_project_id}.iam.gserviceaccount.com"
    triggers_created = []

    try:
        # Get credentials explicitly (uses impersonation in dev mode)
        from app.gcp.credentials import get_credentials, get_credentials_for_client

        # Get credentials for diagnostic logging
        credentials, _ = get_credentials()

        # Initialize Cloud Build client with appropriate credentials
        build_client = get_credentials_for_client(cloudbuild_v1.CloudBuildClient)
        parent = f"projects/{PLATFORM_PROJECT_ID}/locations/{GITHUB_CONNECTION_REGION}"

        # Find the repository resource in the GitHub connection
        from google.cloud.devtools import cloudbuild_v2
        repo_client = get_credentials_for_client(cloudbuild_v2.RepositoryManagerClient)
        connection_path = f"projects/{PLATFORM_PROJECT_ID}/locations/{GITHUB_CONNECTION_REGION}/connections/{GITHUB_CONNECTION_NAME}"

        # List repositories to find matching one
        repository_resource = None
        repo_url = f"https://github.com/{repo_owner}/{repo_name}.git"

        try:
            repositories = repo_client.list_repositories(parent=connection_path)
            for repo in repositories:
                if repo.remote_uri == repo_url:
                    repository_resource = repo.name
                    logger.info(f"Found repository resource: {repository_resource}")
                    break

            if not repository_resource:
                raise HTTPException(
                    status_code=404,
                    detail=f"Repository {repo_url} not found in connection {GITHUB_CONNECTION_NAME}. "
                           f"Please connect the repository at: https://console.cloud.google.com/cloud-build/repositories;region={GITHUB_CONNECTION_REGION}?project={PLATFORM_PROJECT_ID}"
                )
        except Exception as e:
            logger.error(f"Error finding repository: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to find repository in connection: {str(e)}"
            )

        # Create one trigger per environment (orchestrator pattern)
        for env in trigger_config.environments:
            trigger_name = f"{project_id}-{env.name}"

            logger.info(f"Creating Cloud Build trigger: {trigger_name}")

            # Determine trigger source (branch or tag)
            if env.branch_pattern:
                # Use push event with branch filter
                event_config = cloudbuild_v1.RepositoryEventConfig(
                    repository=repository_resource,
                    push=cloudbuild_v1.PushFilter(
                        branch=env.branch_pattern
                    )
                )
            elif env.tag_pattern:
                # Use push event with tag filter
                event_config = cloudbuild_v1.RepositoryEventConfig(
                    repository=repository_resource,
                    push=cloudbuild_v1.PushFilter(
                        tag=env.tag_pattern
                    )
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Environment {env.name} must specify either branch_pattern or tag_pattern"
                )

            # Build trigger configuration - single orchestrator file for all services
            trigger = cloudbuild_v1.BuildTrigger(
                name=trigger_name,
                description=f"Deploy {project.name} (all services) to {env.name}",
                filename="cicd/cloudbuild.yaml",  # Orchestrator file
                repository_event_config=event_config,
                substitutions={
                    "_GCP_PROJECT": project.gcp_project_id or "",
                    "_REGION": project.gcp_region,
                    "_SERVICE_ACCOUNT": deployer_email,
                    "_ENVIRONMENT": env.name,
                    "_ARTIFACT_REPO": f"{SHARED_REGISTRY_LOCATION}-docker.pkg.dev/{PLATFORM_PROJECT_ID}/{SHARED_REGISTRY_REPO}"
                },
                service_account=f"projects/{project.gcp_project_id}/serviceAccounts/{deployer_email}"
                # No approval_config - rely on GitHub branch protection instead
            )

            # ==================== DIAGNOSTIC LOGGING START ====================
            logger.info("=== PERMISSION DIAGNOSTIC START ===")

            # Phase 1: Log the authenticated identity being used
            logger.info(f"Authenticated as: {credentials.service_account_email if hasattr(credentials, 'service_account_email') else 'unknown'}")
            logger.info(f"Credential type: {type(credentials).__name__}")

            # Log what we're trying to do
            logger.info(f"Creating trigger in project: {PLATFORM_PROJECT_ID}")
            service_account_path = f"projects/{project.gcp_project_id}/serviceAccounts/{deployer_email}"
            logger.info(f"Trigger will use service account: {service_account_path}")
            logger.info(f"Client project: {project.gcp_project_id}")

            # Phase 2: Test direct impersonation of the deployer SA
            try:
                from google.cloud.iam_credentials_v1 import IAMCredentialsClient
                from google.cloud.iam_credentials_v1.types import GenerateAccessTokenRequest

                iam_creds_client = IAMCredentialsClient(credentials=credentials)

                # Try to generate access token for the deployer SA (tests actAs permission)
                service_account_name = f"projects/-/serviceAccounts/{deployer_email}"

                logger.info(f"Testing impersonation of: {service_account_name}")

                # Use generateAccessToken to test if we have actAs permission
                request_iam = GenerateAccessTokenRequest(
                    name=service_account_name,
                    scope=["https://www.googleapis.com/auth/cloud-platform"],
                )

                # This will fail with 403 if we don't have actAs permission
                response_iam = iam_creds_client.generate_access_token(request=request_iam)
                logger.info("✓ Successfully tested impersonation - actAs permission is working")

            except Exception as test_error:
                logger.error(f"✗ Failed impersonation test: {test_error}")
                logger.error(f"This indicates the permission issue is with: {credentials.service_account_email if hasattr(credentials, 'service_account_email') else 'the authenticated identity'}")

            # Phase 3: Test permissions using IAM testPermissions API
            try:
                from google.cloud.iam_admin_v1.types import TestIamPermissionsRequest

                iam_admin_client = iam_admin_v1.IAMClient(credentials=credentials)

                # Test permissions on the deployer service account
                resource_name = f"projects/{project.gcp_project_id}/serviceAccounts/{deployer_email}"
                request_test = TestIamPermissionsRequest(
                    resource=resource_name,
                    permissions=[
                        "iam.serviceAccounts.actAs",
                        "iam.serviceAccounts.getAccessToken",
                        "iam.serviceAccounts.implicitDelegation",
                    ]
                )

                response_test = iam_admin_client.test_iam_permissions(request=request_test)
                logger.info(f"Permissions on deployer SA: {list(response_test.permissions)}")

                if "iam.serviceAccounts.actAs" not in response_test.permissions:
                    logger.error("MISSING: iam.serviceAccounts.actAs permission on deployer SA")
                else:
                    logger.info("✓ Has iam.serviceAccounts.actAs permission")

            except Exception as perm_error:
                logger.error(f"Failed to test permissions: {perm_error}")

            # Phase 4: Check Cloud Build permissions
            try:
                # Check if registry-api can create triggers in platform project
                from google.cloud import resourcemanager_v3

                crm_client = resourcemanager_v3.ProjectsClient(credentials=credentials)
                platform_project_obj = crm_client.get_project(name=f"projects/{PLATFORM_PROJECT_ID}")

                logger.info(f"Platform project state: {platform_project_obj.state.name}")

                # Test if we have the cloudbuild.builds.create permission in platform project
                logger.info("Checking Cloud Build permissions in platform project...")

                # List existing triggers to test read permission
                list_request = cloudbuild_v1.ListBuildTriggersRequest(
                    parent=parent,
                    project_id=PLATFORM_PROJECT_ID
                )
                triggers_list = build_client.list_build_triggers(request=list_request)
                logger.info(f"✓ Can list triggers in platform project (found {len(list(triggers_list))} triggers)")

            except Exception as cb_error:
                logger.error(f"Cloud Build permission issue: {cb_error}")

            # Phase 5: Check for cross-project scenario
            if project.gcp_project_id != PLATFORM_PROJECT_ID:
                logger.info(f"CROSS-PROJECT scenario detected:")
                logger.info(f"  Trigger location: {PLATFORM_PROJECT_ID}")
                logger.info(f"  Service account location: {project.gcp_project_id}")
                logger.info("Checking for organization policies that might block cross-project SA usage...")
                logger.info("Consider checking organization policy: constraints/iam.allowedPolicyMemberDomains")

            logger.info("=== PERMISSION DIAGNOSTIC END ===")
            # ==================== DIAGNOSTIC LOGGING END ====================

            try:
                # Log trigger configuration for debugging
                logger.info(f"Trigger config: name={trigger_name}, service_account={service_account_path}, repo={repo_owner}/{repo_name}")

                # Create trigger using request object
                request = cloudbuild_v1.CreateBuildTriggerRequest(
                    parent=parent,
                    project_id=PLATFORM_PROJECT_ID,
                    trigger=trigger
                )
                created_trigger = build_client.create_build_trigger(request=request)
                logger.info(f"Created trigger: {created_trigger.name} (ID: {created_trigger.id})")

                triggers_created.append({
                    'environment': env.name,
                    'trigger_id': created_trigger.id,
                    'trigger_name': created_trigger.name,
                    'branch_pattern': env.branch_pattern,
                    'tag_pattern': env.tag_pattern,
                    'cloudbuild_file': 'cicd/cloudbuild.yaml',
                    'resource_name': created_trigger.resource_name
                })

            except google_exceptions.AlreadyExists:
                logger.info(f"Trigger already exists: {trigger_name}")
                # List existing triggers to find the matching one
                try:
                    list_request = cloudbuild_v1.ListBuildTriggersRequest(
                        parent=parent,
                        project_id=PLATFORM_PROJECT_ID
                    )
                    existing_triggers = build_client.list_build_triggers(request=list_request)

                    for existing in existing_triggers:
                        if existing.name == trigger_name:
                            triggers_created.append({
                                'environment': env.name,
                                'trigger_id': existing.id,
                                'trigger_name': existing.name,
                                'branch_pattern': env.branch_pattern,
                                'tag_pattern': env.tag_pattern,
                                'cloudbuild_file': 'cicd/cloudbuild.yaml',
                                'resource_name': existing.resource_name,
                                'status': 'already_exists'
                            })
                            break
                except Exception as e:
                    logger.error(f"Failed to list existing triggers: {e}")
                    triggers_created.append({
                        'environment': env.name,
                        'trigger_name': trigger_name,
                        'status': 'already_exists_unverified'
                    })

            except Exception as e:
                # Enhanced error logging for diagnostics
                logger.error(f"Failed to create trigger for {env.name}: {e}")
                logger.error(f"Full error: {repr(e)}")
                logger.error(f"Error type: {type(e).__name__}")

                if hasattr(e, 'details'):
                    logger.error(f"Error details: {e.details}")

                if hasattr(e, 'errors'):
                    logger.error(f"Error list: {e.errors}")

                # Try to extract more details from the exception
                if hasattr(e, 'message'):
                    logger.error(f"Error message: {e.message}")

                if hasattr(e, 'metadata'):
                    logger.error(f"Error metadata: {e.metadata}")

                # Log the full exception chain
                import traceback
                logger.error(f"Full traceback:\n{traceback.format_exc()}")

                # Check if it's a permission error and log remediation steps
                if "permission" in str(e).lower():
                    logger.error("PERMISSION ERROR DETECTED")
                    logger.error("Check:")
                    auth_identity = credentials.service_account_email if hasattr(credentials, 'service_account_email') else 'authenticated identity'
                    logger.error(f"  1. Does {auth_identity} have iam.serviceAccounts.actAs on {deployer_email}?")
                    logger.error(f"  2. Does {auth_identity} have cloudbuild.builds.create in {PLATFORM_PROJECT_ID}?")
                    logger.error(f"  3. Are there organization policies blocking cross-project service account usage?")

                raise handle_gcp_error(e, f"Create trigger for {env.name}", trigger_name)

        # Log in audit trail
        db.add(models.AuditLog(
            user_email=current_user,
            action='create_build_triggers',
            entity_type='project',
            entity_id=project_id,
            new_value={
                'github_repo': trigger_config.github_repo_url,
                'triggers': triggers_created
            }
        ))
        db.commit()

        return {
            'status': 'created',
            'github_repo': trigger_config.github_repo_url,
            'triggers': triggers_created
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating build triggers: {e}")
        db.rollback()
        raise handle_gcp_error(e, "Create build triggers", project_id)

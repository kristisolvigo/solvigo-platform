"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


# Client schemas
class ClientBase(BaseModel):
    id: str
    name: str
    subdomain: str
    billing_contact: Optional[str] = None
    technical_contact: Optional[str] = None
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientResponse(ClientBase):
    created_at: datetime
    created_by: Optional[str]
    updated_at: datetime
    status: str

    class Config:
        from_attributes = True


# Project schemas
class ProjectBase(BaseModel):
    id: str
    client_id: str
    name: str
    subdomain: str
    full_domain: str
    gcp_project_id: Optional[str] = None
    gcp_folder_id: Optional[str] = None
    gcp_region: str = "europe-north1"
    github_repo: Optional[str] = None
    terraform_state_bucket: Optional[str] = None
    terraform_state_prefix: Optional[str] = None
    project_type: Optional[str] = None


class ProjectCreate(ProjectBase):
    environments: Optional[List[Dict]] = []
    services: Optional[List[Dict]] = []


class ProjectResponse(ProjectBase):
    created_at: datetime
    created_by: Optional[str]
    updated_at: datetime
    last_deployed_at: Optional[datetime]
    status: str

    class Config:
        from_attributes = True


class ProjectDetail(ProjectResponse):
    """Extended project response with related data"""
    environments: List[Dict]
    services: List[Dict]


# Environment schemas
class EnvironmentBase(BaseModel):
    project_id: str
    name: str
    gcp_project_id: Optional[str] = None
    database_instance: Optional[str] = None
    database_name: Optional[str] = None
    database_type: Optional[str] = None
    auto_deploy: bool = False
    requires_approval: bool = True
    branch_pattern: Optional[str] = None
    tag_pattern: Optional[str] = None


class EnvironmentCreate(EnvironmentBase):
    pass


class EnvironmentResponse(EnvironmentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Service schemas
class ServiceBase(BaseModel):
    project_id: str
    environment_id: Optional[int] = None
    name: str
    type: str
    cloud_run_service: Optional[str] = None
    cloud_run_region: Optional[str] = None
    cloud_run_url: Optional[str] = None
    dockerfile_path: Optional[str] = None
    cloudbuild_file: Optional[str] = None
    artifact_registry_repo: Optional[str] = None


class ServiceCreate(ServiceBase):
    pass


class ServiceResponse(ServiceBase):
    id: int
    current_image: Optional[str]
    current_revision: Optional[str]
    last_deployed_at: Optional[datetime]
    last_deployed_by: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# Deployment schemas
class DeploymentCreate(BaseModel):
    service_id: int
    build_id: Optional[str]
    build_trigger: Optional[str]
    git_commit_sha: Optional[str]
    git_tag: Optional[str]
    git_branch: Optional[str]
    git_author: Optional[str]
    image: str
    deployed_by: Optional[str]
    status: str = "success"
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None


class DeploymentResponse(BaseModel):
    id: int
    service_id: int
    build_id: Optional[str]
    git_commit_sha: Optional[str]
    git_tag: Optional[str]
    image: str
    deployed_at: datetime
    deployed_by: Optional[str]
    status: str

    class Config:
        from_attributes = True


# Subdomain mapping (for load balancer)
class SubdomainMappingResponse(BaseModel):
    full_domain: str
    cloud_run_service: str
    cloud_run_region: str
    cloud_run_url: Optional[str]
    backend_service: Optional[str]
    status: str

    class Config:
        from_attributes = True


# Platform operations schemas
class EnvironmentTriggerConfig(BaseModel):
    """Configuration for a Cloud Build trigger for one environment"""
    name: str
    branch_pattern: Optional[str] = None
    tag_pattern: Optional[str] = None
    cloudbuild_file: str
    require_approval: bool = False


class TriggerConfig(BaseModel):
    """Configuration for creating Cloud Build triggers"""
    github_repo_url: str
    environments: List[EnvironmentTriggerConfig]


class ServiceConfig(BaseModel):
    """Service configuration for CI/CD"""
    name: str
    type: str  # "backend" or "frontend"
    cloudbuild_file: str


class EnhancedTriggerConfig(BaseModel):
    """Enhanced configuration for creating Cloud Build triggers"""
    github_repo_url: str
    services: List[ServiceConfig]
    environments: List[EnvironmentTriggerConfig]


class VPCConfig(BaseModel):
    """Configuration for VPC peering setup"""
    client_project_id: str
    region: str = "europe-north1"


class GCPErrorDetail(BaseModel):
    """Structured error detail for GCP operations"""
    error_type: str
    message: str
    gcp_error_code: Optional[str] = None
    required_permissions: Optional[List[str]] = None
    remediation: Optional[str] = None
    resource_name: Optional[str] = None

"""Domain entities for Solvigo CLI"""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ProjectStatus(Enum):
    """Project status in the system"""
    ACTIVE = "active"
    PENDING_BILLING = "pending_billing"
    SUSPENDED = "suspended"


@dataclass
class Environment:
    """Project environment (dev, prod, etc.)"""
    name: str
    database_instance: Optional[str] = None
    auto_deploy: bool = False
    requires_approval: bool = True


@dataclass
class Service:
    """Cloud Run service configuration"""
    name: str
    type: str
    cloud_run_service: Optional[str] = None
    cloud_run_url: Optional[str] = None
    status: str = "unknown"
    last_deployed_at: Optional[datetime] = None


@dataclass
class ProjectInfo:
    """Full project information from database"""
    id: str
    client_id: str
    name: str
    gcp_project_id: Optional[str]
    full_domain: Optional[str]
    github_repo: Optional[str]
    status: str
    environments: List[Environment]
    services: List[Service]
    gcp_region: Optional[str] = None
    terraform_state_bucket: Optional[str] = None
    last_deployed_at: Optional[datetime] = None
    client_subdomain: Optional[str] = None
    project_subdomain: Optional[str] = None

    @property
    def needs_billing(self) -> bool:
        """Check if project needs billing linked"""
        return self.status == ProjectStatus.PENDING_BILLING.value


@dataclass
class GitRepoInfo:
    """Git repository information"""
    root: str
    branch: str
    remote: Optional[str]
    has_changes: bool

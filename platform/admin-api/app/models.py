"""SQLAlchemy models matching the database schema"""
from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, Text, ForeignKey, Date, DECIMAL, text
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import relationship
from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    subdomain = Column(String(255), unique=True, nullable=False)
    billing_contact = Column(String(255))
    technical_contact = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=text('NOW()'))
    created_by = Column(String(255))
    updated_at = Column(TIMESTAMP, server_default=text('NOW()'), onupdate=text('NOW()'))
    status = Column(String(50), server_default='active')
    notes = Column(Text)

    # Relationships
    projects = relationship("Project", back_populates="client", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(255), primary_key=True)
    client_id = Column(String(255), ForeignKey('clients.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    subdomain = Column(String(255), nullable=False)
    full_domain = Column(String(500), unique=True, nullable=False)

    # GCP Resources
    gcp_project_id = Column(String(255), unique=True)
    gcp_folder_id = Column(String(255))
    gcp_region = Column(String(50), server_default='europe-north1')

    # Code & State
    github_repo = Column(String(500))
    terraform_state_bucket = Column(String(255))
    terraform_state_prefix = Column(String(255))

    # Metadata
    project_type = Column(String(50))
    created_at = Column(TIMESTAMP, server_default=text('NOW()'))
    created_by = Column(String(255))
    updated_at = Column(TIMESTAMP, server_default=text('NOW()'), onupdate=text('NOW()'))
    last_deployed_at = Column(TIMESTAMP)
    status = Column(String(50), server_default='active')

    # Relationships
    client = relationship("Client", back_populates="projects")
    environments = relationship("Environment", back_populates="project", cascade="all, delete-orphan")
    services = relationship("Service", back_populates="project", cascade="all, delete-orphan")


class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(255), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(50), nullable=False)

    # Infrastructure
    gcp_project_id = Column(String(255))
    database_instance = Column(String(255))
    database_name = Column(String(255))
    database_type = Column(String(50))

    # Build Configuration
    auto_deploy = Column(Boolean, server_default='false')
    requires_approval = Column(Boolean, server_default='true')
    branch_pattern = Column(String(255))
    tag_pattern = Column(String(255))

    created_at = Column(TIMESTAMP, server_default=text('NOW()'))

    # Relationships
    project = relationship("Project", back_populates="environments")
    services = relationship("Service", back_populates="environment")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(255), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    environment_id = Column(Integer, ForeignKey('environments.id', ondelete='CASCADE'))

    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)

    # Cloud Run
    cloud_run_service = Column(String(255))
    cloud_run_region = Column(String(50))
    cloud_run_url = Column(String(500))

    # Build Config
    dockerfile_path = Column(String(500))
    cloudbuild_file = Column(String(500))
    artifact_registry_repo = Column(String(500))

    # Status
    current_image = Column(String(500))
    current_revision = Column(String(255))
    last_deployed_at = Column(TIMESTAMP)
    last_deployed_by = Column(String(255))
    status = Column(String(50), server_default='active')

    created_at = Column(TIMESTAMP, server_default=text('NOW()'))

    # Relationships
    project = relationship("Project", back_populates="services")
    environment = relationship("Environment", back_populates="services")
    deployments = relationship("Deployment", back_populates="service", cascade="all, delete-orphan")


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey('services.id', ondelete='CASCADE'), nullable=False)

    # Build Info
    build_id = Column(String(255))
    build_trigger = Column(String(255))
    git_commit_sha = Column(String(40))
    git_tag = Column(String(255))
    git_branch = Column(String(255))
    git_author = Column(String(255))

    # Deployment
    image = Column(String(500))
    deployed_at = Column(TIMESTAMP, server_default=text('NOW()'))
    deployed_by = Column(String(255))

    # Status
    status = Column(String(50))
    duration_seconds = Column(Integer)
    error_message = Column(Text)

    created_at = Column(TIMESTAMP, server_default=text('NOW()'))

    # Relationships
    service = relationship("Service", back_populates="deployments")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    role = Column(String(50), nullable=False)

    created_at = Column(TIMESTAMP, server_default=text('NOW()'))
    last_login_at = Column(TIMESTAMP)
    status = Column(String(50), server_default='active')


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(String(255))

    # Change Details
    old_value = Column(JSONB)
    new_value = Column(JSONB)

    # Context
    ip_address = Column(INET)
    user_agent = Column(String(500))
    request_id = Column(String(255))

    created_at = Column(TIMESTAMP, server_default=text('NOW()'))

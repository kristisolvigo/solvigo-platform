"""Project management endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.auth import get_current_user
from app import models, schemas

router = APIRouter()


@router.post("/", response_model=schemas.ProjectResponse, status_code=201)
def register_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Register a new project (called by CLI during import/init).

    Automatically creates associated environments and services.
    """
    # Check if project already exists
    existing = db.query(models.Project).filter(models.Project.id == project.id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Project {project.id} already exists")

    # Create project
    db_project = models.Project(
        **project.dict(exclude={'environments', 'services'}),
        created_by=current_user
    )
    db.add(db_project)

    # Create environments
    for env_data in project.environments or []:
        db_env = models.Environment(**env_data, project_id=project.id)
        db.add(db_env)

    # Flush to get environment IDs
    db.flush()

    # Create services
    for svc_data in project.services or []:
        # Find environment by name
        env_name = svc_data.get('environment', 'prod')
        env = db.query(models.Environment).filter(
            models.Environment.project_id == project.id,
            models.Environment.name == env_name
        ).first()

        db_service = models.Service(
            **{k: v for k, v in svc_data.items() if k != 'environment'},
            project_id=project.id,
            environment_id=env.id if env else None
        )
        db.add(db_service)

    # Log in audit trail
    db.add(models.AuditLog(
        user_email=current_user,
        action='create_project',
        entity_type='project',
        entity_id=project.id,
        new_value={'project': project.dict()}
    ))

    db.commit()
    db.refresh(db_project)

    return db_project


@router.get("/", response_model=List[schemas.ProjectResponse])
def list_projects(
    client_id: Optional[str] = None,
    status: Optional[str] = 'active',
    db: Session = Depends(get_db)
):
    """
    List all projects, optionally filtered by client.

    Public endpoint (no auth required) for load balancer to query.
    """
    query = db.query(models.Project)

    if client_id:
        query = query.filter(models.Project.client_id == client_id)

    if status:
        query = query.filter(models.Project.status == status)

    return query.all()


@router.get("/{project_id}", response_model=schemas.ProjectDetail)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """
    Get project details with all related environments and services.
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Build detailed response
    return {
        **project.__dict__,
        'environments': [
            {
                'id': env.id,
                'name': env.name,
                'database_instance': env.database_instance,
                'auto_deploy': env.auto_deploy,
                'requires_approval': env.requires_approval
            }
            for env in project.environments
        ],
        'services': [
            {
                'id': svc.id,
                'name': svc.name,
                'type': svc.type,
                'cloud_run_service': svc.cloud_run_service,
                'cloud_run_url': svc.cloud_run_url,
                'status': svc.status,
                'last_deployed_at': svc.last_deployed_at
            }
            for svc in project.services
        ]
    }


@router.patch("/{project_id}/subdomain")
def update_subdomain(
    project_id: str,
    new_subdomain: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Update project subdomain (triggers load balancer update)"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    old_subdomain = project.subdomain
    old_domain = project.full_domain

    # Update subdomain and full_domain
    project.subdomain = new_subdomain
    client_subdomain = db.query(models.Client.subdomain).filter(
        models.Client.id == project.client_id
    ).scalar()
    project.full_domain = f"{new_subdomain}.{client_subdomain}.solvigo.ai"
    project.updated_at = datetime.utcnow()

    # Log in audit trail
    db.add(models.AuditLog(
        user_email=current_user,
        action='update_subdomain',
        entity_type='project',
        entity_id=project_id,
        old_value={'subdomain': old_subdomain, 'full_domain': old_domain},
        new_value={'subdomain': new_subdomain, 'full_domain': project.full_domain}
    ))

    db.commit()

    return {"status": "updated", "full_domain": project.full_domain}

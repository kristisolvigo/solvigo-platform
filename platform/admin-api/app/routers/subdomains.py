"""Subdomain mapping endpoints for load balancer integration"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, List

from app.database import get_db
from app import models

router = APIRouter()


@router.get("/")
def get_all_subdomain_mappings(db: Session = Depends(get_db)) -> Dict:
    """
    Get all subdomain mappings for load balancer configuration.

    Returns mapping of domain → service details.
    No authentication required (called by load balancer Terraform).
    """
    # Query all active projects with their services
    projects = db.query(models.Project).filter(
        models.Project.status == 'active'
    ).all()

    mappings = {}

    for project in projects:
        for service in project.services:
            if service.status != 'active' or not service.cloud_run_service:
                continue

            # Get environment name
            env = db.query(models.Environment).filter(
                models.Environment.id == service.environment_id
            ).first()

            env_name = env.name if env else 'prod'

            # Build domain name
            # Format: {service-type}-{env}.{project}.{client}.solvigo.ai
            # Or just: {project}.{client}.solvigo.ai for prod frontend
            if service.type == 'frontend' and env_name == 'prod':
                # Main domain for frontend prod
                domain = project.full_domain
            else:
                # Subdomain for other services
                service_prefix = f"{service.type}-{env_name}" if env_name != 'prod' else service.type
                client_subdomain = db.query(models.Client.subdomain).filter(
                    models.Client.id == project.client_id
                ).scalar()
                domain = f"{service_prefix}.{project.subdomain}.{client_subdomain}.solvigo.ai"

            mappings[domain] = {
                'cloud_run_service': service.cloud_run_service,
                'cloud_run_region': service.cloud_run_region or 'europe-north1',
                'cloud_run_url': service.cloud_run_url,
                'project_id': project.id,
                'client_id': project.client_id,
                'service_type': service.type,
                'environment': env_name
            }

    return mappings


@router.get("/{domain}")
def get_subdomain_mapping(domain: str, db: Session = Depends(get_db)) -> Dict:
    """
    Get mapping for a specific domain.

    No authentication required.
    """
    mappings = get_all_subdomain_mappings(db)

    if domain not in mappings:
        return {"error": "Domain not found", "domain": domain}

    return mappings[domain]

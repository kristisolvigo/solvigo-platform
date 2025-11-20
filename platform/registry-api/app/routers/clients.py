"""Client management endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app import models, schemas

router = APIRouter()


@router.post("/", response_model=schemas.ClientResponse, status_code=201)
def register_client(
    client: schemas.ClientCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Register a new client (called by CLI)"""
    # Check if client already exists
    existing = db.query(models.Client).filter(models.Client.id == client.id).first()
    if existing:
        # Return existing client (idempotent)
        return existing

    # Create new client
    db_client = models.Client(**client.dict(), created_by=current_user)
    db.add(db_client)

    # Log in audit trail
    db.add(models.AuditLog(
        user_email=current_user,
        action='create_client',
        entity_type='client',
        entity_id=client.id,
        new_value={'client': client.dict()}
    ))

    db.commit()
    db.refresh(db_client)

    return db_client


@router.get("/", response_model=List[schemas.ClientResponse])
def list_clients(
    status: str = 'active',
    db: Session = Depends(get_db)
):
    """List all clients (no auth required for load balancer)"""
    query = db.query(models.Client)

    if status:
        query = query.filter(models.Client.status == status)

    return query.all()


@router.get("/{client_id}", response_model=schemas.ClientResponse)
def get_client(client_id: str, db: Session = Depends(get_db)):
    """Get client details"""
    client = db.query(models.Client).filter(models.Client.id == client_id).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return client

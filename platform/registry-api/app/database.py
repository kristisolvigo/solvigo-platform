"""Database connection using Cloud SQL Python Connector with IAM auth"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from google.cloud.sql.connector import Connector

# Cloud SQL connection details
INSTANCE_CONNECTION_NAME = os.getenv(
    'INSTANCE_CONNECTION_NAME',
    'solvigo-platform-prod:europe-north1:solvigo-registry'
)
DB_USER = os.getenv('DB_USER', 'registry-api@solvigo-platform-prod.iam')
DB_NAME = os.getenv('DB_NAME', 'registry')

# Initialize Cloud SQL Connector
connector = Connector()


def getconn():
    """Create database connection using Cloud SQL Connector with IAM auth"""
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pg8000",
        user=DB_USER,
        db=DB_NAME,
        enable_iam_auth=True,
        ip_type="PRIVATE",
    )
    return conn


# Create SQLAlchemy engine
engine = create_engine(
    "postgresql+pg8000://",
    creator=getconn,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

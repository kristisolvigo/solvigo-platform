"""Database connection - supports both Cloud SQL and local PostgreSQL"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Check if we should use Cloud SQL or local PostgreSQL
USE_CLOUD_SQL = os.getenv('USE_CLOUD_SQL', 'true').lower() == 'true'
DATABASE_URL = os.getenv('DATABASE_URL')

if USE_CLOUD_SQL and not DATABASE_URL:
    # Cloud SQL with IAM auth
    from google.cloud.sql.connector import Connector

    # Cloud SQL connection details
    INSTANCE_CONNECTION_NAME = os.getenv(
        'INSTANCE_CONNECTION_NAME',
        'solvigo-platform-prod:europe-north1:solvigo-registry'
    )
    DB_USER = os.getenv('DB_USER', 'admin-api@solvigo-platform-prod.iam')
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

    # Create SQLAlchemy engine with Cloud SQL
    engine = create_engine(
        "postgresql+pg8000://",
        creator=getconn,
    )
elif DATABASE_URL:
    # Local PostgreSQL or direct connection via DATABASE_URL
    engine = create_engine(DATABASE_URL)
else:
    raise ValueError(
        "Either USE_CLOUD_SQL must be true with Cloud SQL config, "
        "or DATABASE_URL must be set for direct PostgreSQL connection"
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

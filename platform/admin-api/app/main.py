"""Solvigo Registry API - FastAPI application"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

from app.routers import clients, projects, subdomains, platform
from app import __version__

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Solvigo Admin API",
    description="Central admin API for managing Solvigo client projects",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware (allow CLI and dashboard to access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to solvigo domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests"""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Log request
    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} "
        f"- {response.status_code} "
        f"- {duration:.3f}s "
        f"- {request.client.host if request.client else 'unknown'}"
    )

    return response


# Include routers
app.include_router(clients.router, prefix="/api/v1/clients", tags=["clients"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(subdomains.router, prefix="/api/v1/subdomains", tags=["subdomains"])
app.include_router(platform.router, prefix="/api/v1/platform", tags=["platform"])


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint for Cloud Run"""
    return {
        "status": "healthy",
        "version": __version__,
        "service": "admin-api"
    }


# Root endpoint
@app.get("/")
def root():
    """API information"""
    return {
        "service": "Solvigo Admin API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health"
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

# app/main.py

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from .config import settings
from .endpoints.admin import admin_router, token_router
from .endpoints.claims import claims_router
from .limiter import limiter
from .logger import get_logger

logger = get_logger(__name__)

logger.info("Starting Mediclaim Processing API...")

app = FastAPI(
    title="Mediclaim Processing API",
    description="API for extracting and adjudicating medical claims.",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event():
    logger.info("Application startup event triggered.")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown event triggered.")


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware initialized.")

app.include_router(claims_router, prefix="/api/v1/claims", tags=["Claims"])
app.include_router(token_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
logger.info("Routers initialized.")


@app.get("/", tags=["Health Check"])
@limiter.limit("5/minute")  # Protect the health check endpoint as well
def read_root(request: Request):
    """just for test"""
    return {"status": "ok"}

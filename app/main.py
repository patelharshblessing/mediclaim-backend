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

app = FastAPI(
    title="Mediclaim Processing API",
    description="API for extracting and adjudicating medical claims.",
    version="1.0.0",
)

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

app.include_router(claims_router, prefix="/api/v1/claims", tags=["Claims"])
app.include_router(token_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
#  Add the limiter to the app's state
# app.state.limiter = limiter


# # Add a custom exception handler for rate limit exceeded errors
# @app.exception_handler(RateLimitExceeded)
# async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
#     return JSONResponse(
#         status_code=429,
#         content={"detail": f"Rate limit exceeded: {exc.detail}"}
#     )


# Include the router from our endpoints file
@app.get("/", tags=["Health Check"])
@limiter.limit("5/minute")  # Protect the health check endpoint as well
def read_root(request: Request):
    """just for test"""
    return {"status": "ok"}

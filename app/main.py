# app/main.py

from fastapi import FastAPI
from .endpoints import router as api_router
from .limiter import limiter
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from fastapi.requests import Request


app = FastAPI(
    title="Mediclaim Processing API",
    description="API for extracting and adjudicating medical claims.",
    version="1.0.0"
)

#  Add the limiter to the app's state
app.state.limiter = limiter

# Add a custom exception handler for rate limit exceeded errors
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"}
    )




# Include the router from our endpoints file
app.include_router(api_router, prefix="/api/v1", tags=["Claims"])
@app.get("/", tags=["Health Check"])
@limiter.limit("5/minute") # Protect the health check endpoint as well
def read_root(request: Request):
    return {"status": "ok"}


"""
HackOps FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine
from app.core.redis import init_redis, close_redis
from app.api.v1 import auth, events, teams, submissions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting HackOps application...")
    try:
        await init_redis()
        print("Redis connection initialized")
    except Exception as e:
        print(f"Failed to initialize Redis: {e}")
    
    yield
    
    # Shutdown
    print("Shutting down HackOps application...")
    try:
        await close_redis()
        print("Redis connection closed")
    except Exception as e:
        print(f"Error closing Redis: {e}")


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="HackOps API",
        description="End-to-end hackathon organizing and execution platform",
        version=settings.VERSION,
        lifespan=lifespan,
        debug=settings.DEBUG
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.VERSION
        }

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "Welcome to HackOps API",
            "version": settings.VERSION,
            "docs": "/docs"
        }

    # Include API routers
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
    app.include_router(events.router, prefix="/api/v1/events", tags=["events"])
    app.include_router(teams.router, prefix="/api/v1/teams", tags=["teams"])
    app.include_router(submissions.router, prefix="/api/v1/submissions", tags=["submissions"])

    return app


app = create_application()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
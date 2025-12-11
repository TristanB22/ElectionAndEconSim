#!/usr/bin/env python3
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
import time

# Setup paths
from Utils.path_manager import initialize_paths
initialize_paths()

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
try:
    from Utils.env_loader import load_environment
    load_environment(env_path)
except ImportError:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)

# Import configuration and routers
from .config import settings
from .routers import (
    geospatial_router,
    financial_router,
    simulation_router,
    economic_router,
    map_router,
    utility_router,
    routing_router,
    agent_router,
)

# Import middleware components
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse


class SecurityAndContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle:
    1. API key authentication for /api/* routes (if API key is configured)
    2. Extracting simulation_id from headers or query params
    """
    
    async def dispatch(self, request: StarletteRequest, call_next):
        # Extract simulation_id from header or query param
        sim_id = request.headers.get("X-Simulation-Id")
        if not sim_id and request.url.query:
            # Parse query string for simulation_id
            from urllib.parse import parse_qs
            params = parse_qs(request.url.query)
            sim_id = params.get("simulation_id", [None])[0]
        
        # Store in request state for later use
        request.state.simulation_id = sim_id
        
        # Check API key for /api/* routes (optional based on settings)
        if request.url.path.startswith("/api/"):
            if settings.API_KEY:
                provided_key = request.headers.get("X-API-Key")
                if provided_key != settings.API_KEY:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid or missing API key"}
                    )
        
        # Continue with request
        response = await call_next(request)
        
        # Add simulation_id to response headers if present
        if sim_id:
            response.headers["X-Simulation-Id"] = sim_id
        return response


# Initialize FastAPI application
app = FastAPI(
    title="World_Sim Reporting API",
    description="Backend API for World Simulation reporting and analysis",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=settings.ALLOW_CREDENTIALS,
    allow_methods=settings.ALLOW_METHODS,
    allow_headers=settings.ALLOW_HEADERS,
)

# Add compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add security and context middleware
app.add_middleware(SecurityAndContextMiddleware)

# Register all routers
app.include_router(utility_router)
app.include_router(financial_router)
app.include_router(simulation_router)
app.include_router(economic_router)
app.include_router(map_router)
app.include_router(geospatial_router)
app.include_router(routing_router)
app.include_router(agent_router)


@app.on_event("startup")
async def startup_event():
    """Initialize API startup process."""
    print("=" * 80)
    print("World_Sim Reporting API Starting Up")
    print("=" * 80)
    print(f"API Key Required: {'Yes' if settings.API_KEY else 'No'}")
    print(f"CORS Origins: {settings.ALLOW_ORIGINS}")
    print("Registered Routers:")
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            print(f"  {list(route.methods)[0] if route.methods else 'GET':6s} {route.path}")
    print("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("World_Sim Reporting API Shutting Down")


@app.get("/health")
def health_check():
    """Health check endpoint to verify API status."""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "service": "World_Sim Reporting API",
            "routers": [
                "geospatial", "financial", "simulation",
                "economic", "map", "utility", "routing", "agent"
            ]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "service": "World_Sim Reporting API"
        }


@app.get("/api/simulation/debug")
def get_simulation_debug(request: Request):
    """Debug endpoint to verify simulation_id capture (secured by API key if configured)."""
    return {
        "simulation_id": getattr(request.state, "simulation_id", None),
        "headers": dict(request.headers),
        "query_params": dict(request.query_params)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import List


def _to_bool(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def _strip_quotes(val: str | None) -> str | None:
    if val is None:
        return None
    if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
        return val[1:-1]
    return val


class Settings:
    """Centralized configuration for the Reporting API."""

    def __init__(self) -> None:
        # Load .env via centralized loader if available
        env_path = Path(__file__).parent.parent / ".env"
        try:
            from Utils.env_loader import load_environment  # type: ignore
            load_environment(env_path)
        except Exception:
            try:
                from dotenv import load_dotenv  # type: ignore
                load_dotenv(dotenv_path=env_path)
            except Exception:
                pass

        # API
        self.API_TITLE: str = os.getenv("REPORTING_API_TITLE", "World_Sim Reporting API")
        self.API_VERSION: str = os.getenv("REPORTING_API_VERSION", "2.0.0")
        self.DEBUG: bool = _to_bool(os.getenv("DEBUG"), False)

        # Security
        self.API_KEY: str | None = _strip_quotes(os.getenv("REPORTING_API_KEY"))
        self.ALLOW_ORIGINS: List[str] = [
            s.strip() for s in os.getenv(
                "CORS_ALLOW_ORIGINS",
                "http://localhost:3000,http://localhost:3001,http://localhost:5173",
            ).split(",") if s.strip()
        ]
        self.ALLOW_CREDENTIALS: bool = _to_bool(os.getenv("CORS_ALLOW_CREDENTIALS"), True)
        self.ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.ALLOW_HEADERS: List[str] = [
            "*",
        ]

        # MySQL
        self.MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
        self.MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
        self.MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
        self.MYSQL_PASSWORD: str = _strip_quotes(os.getenv("MYSQL_PASSWORD", "")) or ""
        self.MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "world_sim")

        # PostGIS
        self.POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
        self.POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
        self.POSTGRES_PASSWORD: str = _strip_quotes(os.getenv("POSTGRES_PASSWORD", "")) or ""
        self.POSTGRES_DB: str = os.getenv("POSTGRES_DB", "gis")

        # Roads / Geospatial behavior
        # If True, enforce LIMITs on road queries; if False, no LIMIT (may return many rows)
        self.ROADS_ENFORCE_LIMITS: bool = _to_bool(os.getenv("ROADS_ENFORCE_LIMITS"), False)
        # If True, include previously excluded route types (footway, path, cycleway, etc.)
        self.ROADS_INCLUDE_EXCLUDED: bool = _to_bool(os.getenv("ROADS_INCLUDE_EXCLUDED"), True)
        # Hard upper bound on POIs returned from PostGIS for a single spatial query
        # This protects the database from accidentally huge LIMIT values.
        self.POIS_MAX_POINTS: int = int(os.getenv("POIS_MAX_POINTS", "500000"))

        # Tiles / Proxy settings
        # Comma-separated list of proxy URLs (e.g., http://user:pass@host:port)
        self.TILE_HTTP_PROXIES: List[str] = [
            p.strip() for p in os.getenv("TILE_HTTP_PROXIES", "").split(",") if p.strip()
        ]
        # Whether to use the HTTP proxy pool for upstream tile fetches (default: True)
        self.USE_TILE_PROXY: bool = _to_bool(os.getenv("USE_TILE_PROXY", "true"), True)
        # Optional custom upstream tile URL template
        self.TILE_UPSTREAM_URL: str = os.getenv(
            "TILE_UPSTREAM_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        )
        # Retry/backoff configuration
        self.TILE_MAX_RETRIES: int = int(os.getenv("TILE_MAX_RETRIES", "5"))
        self.TILE_BACKOFF_BASE_MS: int = int(os.getenv("TILE_BACKOFF_BASE_MS", "200"))
        self.TILE_TIMEOUT_S: float = float(os.getenv("TILE_TIMEOUT_S", "10"))
        # Local tiles directory (NAS) for cached/seeded tiles
        self.NAS_MAPS_DATA_DIRECTORY: str = os.getenv(
            "NAS_MAPS_DATA_DIRECTORY", "/Volumes/Master Data/OpenStreetMap"
        )

        # Valhalla Routing Configuration
        self.VALHALLA_HOST: str = os.getenv("VALHALLA_HOST", "192.168.0.164")
        self.VALHALLA_PORT: int = int(os.getenv("VALHALLA_PORT", "5433"))
        self.VALHALLA_BASE_URL: str = f"http://{self.VALHALLA_HOST}:{self.VALHALLA_PORT}"
        self.VALHALLA_TIMEOUT: float = float(os.getenv("VALHALLA_TIMEOUT", "30.0"))

        # Routing defaults
        self.ROUTING_DEFAULT_MODE: str = os.getenv("ROUTING_DEFAULT_MODE", "auto")
        self.ROUTING_DEFAULT_UNITS: str = os.getenv("ROUTING_DEFAULT_UNITS", "miles")
        self.ROUTING_MAX_ALTERNATES: int = int(os.getenv("ROUTING_MAX_ALTERNATES", "3"))

        # Tile logging verbosity (hardcoded in config, not from env)
        # 0 = silent (errors only), 1 = basic (config + final status), 2 = verbose (all attempts + responses)
        self.TILE_LOG_LEVEL: int = 0

        # Agent visualization settings
        self.AGENT_MARKER_COLOR: str = os.getenv("AGENT_MARKER_COLOR", "#60a5fa")  # blue-400
        self.AGENT_MARKER_SIZE: int = int(os.getenv("AGENT_MARKER_SIZE", "8"))
        self.AGENT_MIN_ZOOM: int = int(os.getenv("AGENT_MIN_ZOOM", "8"))
        self.AGENT_CLUSTER_RADIUS: int = int(os.getenv("AGENT_CLUSTER_RADIUS", "50"))


settings = Settings()



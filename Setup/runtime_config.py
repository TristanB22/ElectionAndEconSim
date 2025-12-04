#!/usr/bin/env python3
"""
Centralized runtime configuration for World_Sim.

- Reads environment variables
- Exposes service endpoints (Qdrant, phpMyAdmin, Grafana)
- Exposes common data paths (L2, OSM test, Google Maps test)
- Computes database names (agents, firms, simulations)

Usage:
    from Setup.runtime_config import init_runtime, get_runtime
    init_runtime()
    cfg = get_runtime()
    print(cfg.services.qdrant_base_url)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ServicesConfig:
    qdrant_host: str
    qdrant_http_port: int
    phpmyadmin_port: int
    grafana_port: int

    @property
    def qdrant_base_url(self) -> str:
        # Docker maps 6333->1002 by default in this project
        return f"http://{self.qdrant_host}:{self.qdrant_http_port}"

    @property
    def phpmyadmin_url(self) -> str:
        return f"http://localhost:{self.phpmyadmin_port}"

    @property
    def grafana_url(self) -> str:
        return f"http://localhost:{self.grafana_port}"

    def qdrant_collections_url(self) -> str:
        return f"{self.qdrant_base_url}/collections"

    def qdrant_collection_url(self, name: str) -> str:
        return f"{self.qdrant_base_url}/collections/{name}"


@dataclass
class PathsConfig:
    l2_data_dir: Optional[str]
    test_l2_file: Optional[str]
    osm_test_dir: Optional[str]
    google_maps_test_dir: Optional[str]


@dataclass
class DatabaseNames:
    base: str
    agents: str
    firms: str
    simulations: str


@dataclass
class RuntimeConfig:
    services: ServicesConfig
    paths: PathsConfig
    db_names: DatabaseNames
    openrouter_key: Optional[str]


_RUNTIME: Optional[RuntimeConfig] = None


def init_runtime() -> RuntimeConfig:
    """Initialize and cache runtime configuration from environment variables."""
    global _RUNTIME

    # Services
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    # In docker-compose we expose 1002->6333; prefer 1002
    qdrant_http_port = int(os.getenv("QDRANT_PORT", "1002"))
    phpmyadmin_port = int(os.getenv("PHPMYADMIN_PORT", "1005"))
    grafana_port = int(os.getenv("GRAFANA_PORT", "1006"))

    services = ServicesConfig(
        qdrant_host=qdrant_host,
        qdrant_http_port=qdrant_http_port,
        phpmyadmin_port=phpmyadmin_port,
        grafana_port=grafana_port,
    )

    # Paths
    paths = PathsConfig(
        l2_data_dir=os.getenv("L2_DATA_DIR"),
        test_l2_file=os.getenv("TEST_L2_DATA_FILE"),
        osm_test_dir=os.getenv("TESTING_OSM_DATA_DIRECTORY"),
        google_maps_test_dir=os.getenv("TESTING_GOOGLE_MAPS_DATA_DIRECTORY"),
    )

    # Database names
    base_db = os.getenv("DB_NAME", "world_sim")
    db_names = DatabaseNames(
        base=base_db,
        agents=f"{base_db}_agents",
        firms=f"{base_db}_firms",
        simulations=f"{base_db}_simulations",
    )

    _RUNTIME = RuntimeConfig(
        services=services,
        paths=paths,
        db_names=db_names,
        openrouter_key=os.getenv("OPENROUTER_KEY"),
    )
    return _RUNTIME


def get_runtime() -> RuntimeConfig:
    """Return initialized runtime configuration (call init_runtime first)."""
    global _RUNTIME
    if _RUNTIME is None:
        return init_runtime()
    return _RUNTIME




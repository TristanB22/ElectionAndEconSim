#!/usr/bin/env python3
"""
Helper script to identify which endpoints in api.py are now handled by routers.
"""

# Endpoints migrated to routers:
MIGRATED_ENDPOINTS = {
    "map_router": [
        "GET /api/map/config",
        "GET /api/map/tiles/{z}/{x}/{y}.png",
    ],
    "simulation_router": [
        "GET /firms",
        "GET /simulations",
        "POST /simulations",
        "GET /simulations/{simulation_id}",
        "PUT /simulations/{simulation_id}/status",
        "POST /simulations/{simulation_id}/complete",
        "GET /firms/{firm_id}/defaults",
    ],
    "financial_router": [
        "GET /statements",
        "GET /financial_statements",
        "GET /transactions",
        "GET /estimate_columns",
        "GET /verify",
        "GET /export_excel",
    ],
    "economic_router": [
        "GET /gdp/current",
        "GET /gdp/periods",
        "GET /gdp/sectors",
    ],
    "geospatial_router": [
        "GET /api/pois/spatial",
        "GET /api/pois/spatial/heatmap",
        "GET /api/pois/spatial/{osm_id}",
        "GET /api/pois/spatial/status",
        "GET /api/roads/spatial",
        "GET /api/buildings/spatial",
        "GET /api/addresses/search",
    ],
    "utility_router": [
        "POST /init_reporting_schema",
        "POST /populate_sample_data",
    ],
}

# Endpoints to keep in api.py (not migrated):
KEEP_ENDPOINTS = [
    "GET /health",
    "GET /api/simulation/debug",
]

print("Endpoints migrated to routers:")
for router, endpoints in MIGRATED_ENDPOINTS.items():
    print(f"\n{router}:")
    for ep in endpoints:
        print(f"  - {ep}")

print(f"\n\nTotal migrated: {sum(len(v) for v in MIGRATED_ENDPOINTS.values())}")
print(f"Total kept: {len(KEEP_ENDPOINTS)}")


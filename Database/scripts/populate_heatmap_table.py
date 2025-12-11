#!/usr/bin/env python3
"""
Populate POI Master Heatmap Table using centralized DB managers.

- Reads random coordinates from PostGIS via PostGISGeoDatabaseManager
- Writes to MySQL `poi_master_heatmap` via DatabaseManager connection pools
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import time
import argparse

# Ensure World_Sim root is on sys.path for direct script execution
_world_sim_root = Path(__file__).resolve().parents[2]
if str(_world_sim_root) not in sys.path:
    sys.path.insert(0, str(_world_sim_root))

# Initialize path management (idempotent) and load environment
try:
    from Utils.path_manager import initialize_paths
    initialize_paths()
except Exception:
    pass
try:
    from Utils.env_loader import load_environment
    load_environment(_world_sim_root / ".env")
except Exception:
    pass

from Database.connection_manager import get_db_manager
from Database.geo_database_manager_postgis import get_geo_database_manager


def _get_geo_db_name() -> str:
    return os.getenv('DB_GEO_NAME', 'world_sim_geo')


def create_heatmap_table() -> None:
    print("Creating poi_master_heatmap table if it doesn't exist...")
    create_sql = """
        CREATE TABLE IF NOT EXISTS poi_master_heatmap (
            lat DECIMAL(10, 8) NOT NULL,
            lon DECIMAL(11, 8) NOT NULL,
            PRIMARY KEY (lat, lon),
            INDEX idx_poi_master_heatmap_lat_lon (lat, lon)
        )
    """
    dbm = get_db_manager()
    res = dbm.execute_query(create_sql, database=_get_geo_db_name(), fetch=False)
    if not res.success:
        raise RuntimeError(res.error or 'Failed to create table')
    print("Table ready")


def clear_heatmap_table() -> None:
    print("Clearing poi_master_heatmap table...")
    dbm = get_db_manager()
    res = dbm.execute_query("DELETE FROM poi_master_heatmap", database=_get_geo_db_name(), fetch=False)
    if not res.success:
        raise RuntimeError(res.error or 'Failed to clear table')
    print("Table cleared")


def fetch_pois_from_postgis(count: int, testing: bool = False) -> List[Dict[str, Any]]:
    mgr = get_geo_database_manager()
    return mgr.fetch_point_coords(count=count, testing=testing)


def populate_heatmap_table(count: int, clear_first: bool = True, testing: bool = False) -> None:
    coord_type = "first" if testing else "random"
    print(f"Populating poi_master_heatmap table with {count:,} {coord_type} POI coordinates...")
    print(f"   Data source: PostGIS planet_osm_point (central manager)")
    print(f"   Storage: MySQL poi_master_heatmap (central manager)")

    start_time = time.perf_counter()

    # Fetch coords first
    rows = fetch_pois_from_postgis(count, testing)
    if not rows:
        print("No coordinates found!")
        return

    # Ensure table exists and optionally clear
    create_heatmap_table()
    if clear_first:
        clear_heatmap_table()

    # Insert coordinates in batches
    coordinates = [(row['lat'], row['lon']) for row in rows]
    insert_sql = """
        INSERT INTO poi_master_heatmap (lat, lon) 
        VALUES (%s, %s) 
        ON DUPLICATE KEY UPDATE
            lat = VALUES(lat),
            lon = VALUES(lon)
    """

    dbm = get_db_manager()
    batch_size = 5000
    inserted_count = 0
    total_batches = (len(coordinates) + batch_size - 1) // batch_size
    print(f"   Inserting {len(coordinates):,} coordinates in {total_batches} batches of {batch_size:,}...")

    insert_start = time.perf_counter()
    for i in range(0, len(coordinates), batch_size):
        batch = coordinates[i:i + batch_size]
        batch_num = i // batch_size + 1
        try:
            res = dbm.execute_many(insert_sql, batch, database=_get_geo_db_name())
            if not res.success:
                raise RuntimeError(res.error or 'Batch insert failed')
            inserted_count += len(batch)
            print(f"   Batch {batch_num}/{total_batches}: Inserted {len(batch):,} coordinates ({inserted_count:,}/{len(coordinates):,})")
        except Exception as e:
            print(f"   Batch insert error: {e}")
            print(f"   Falling back to individual inserts for batch {batch_num}...")
            for coord in batch:
                try:
                    res2 = dbm.execute_query(insert_sql, coord, database=_get_geo_db_name(), fetch=False)
                    if res2.success:
                        inserted_count += 1
                except Exception as single_error:
                    print(f"   Individual insert warning: {single_error}")

    insert_time = time.perf_counter() - insert_start
    print(f"   Insert completed in {insert_time:.2f}s")
    print(f"   Inserted {inserted_count:,} coordinates")

    # Verify count
    verify = dbm.execute_query("SELECT COUNT(*) as count FROM poi_master_heatmap", database=_get_geo_db_name(), fetch=True)
    if verify.success and verify.data:
        final_count = verify.data[0].get('count') or list(verify.data[0].values())[0]
        print(f"   Final table count: {final_count:,}")

    total_time = time.perf_counter() - start_time
    print("\nHeatmap table populated successfully!")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Coordinates inserted: {inserted_count:,}")
    print(f"   Rate: {inserted_count/total_time:.0f} coordinates/second")


def main():
    parser = argparse.ArgumentParser(description="Populate POI master heatmap table with coordinates")
    parser.add_argument("--count", type=int, nargs='?', const=100000, default=100000,
                       help="Number of POI coordinates to insert (default: 100,000)")
    parser.add_argument("--no-clear", action="store_true",
                       help="Don't clear the table before inserting new data (default: clear table)")
    parser.add_argument("--testing", action="store_true",
                       help="Use first n records instead of random (faster for testing)")

    args = parser.parse_args()
    if args.count <= 0:
        print("Count must be positive")
        sys.exit(1)

    clear_table = not args.no_clear
    populate_heatmap_table(args.count, clear_table, args.testing)


if __name__ == "__main__":
    main()



#!/usr/bin/env python3
"""
Load OpenAddresses NDJSON/GeoJSON features into the centralized geo database using
Database.connection_manager. No direct connector use here.
"""

import json
import sys
import argparse
import time
from typing import List, Dict, Any, Optional, Tuple
import os
from pathlib import Path

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


def _geo_db_name() -> str:
    return os.getenv('DB_GEO_NAME', 'world_sim_geo')


def parse_geojson_line(line: str) -> Optional[Dict[str, Any]]:
    try:
        feature = json.loads(line.strip())
        if feature.get('type') != 'Feature':
            return None
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        if geometry.get('type') != 'Point':
            return None
        coordinates = geometry.get('coordinates', [])
        if len(coordinates) != 2:
            return None
        lon, lat = coordinates
        address_data = {
            'hash': properties.get('hash', ''),
            'number': int(properties.get('number', 0)) if str(properties.get('number', '')).isdigit() else None,
            'street': properties.get('street', ''),
            'unit': properties.get('unit', ''),
            'city': properties.get('city', ''),
            'district': properties.get('district', ''),
            'region': properties.get('region', ''),
            'postcode': properties.get('postcode', ''),
            'id': properties.get('id', ''),
            'lat': float(lat),
            'lon': float(lon)
        }
        return address_data
    except Exception:
        return None


def insert_addresses_batch(addresses: List[Dict[str, Any]]) -> int:
    if not addresses:
        return 0
    insert_query = """
    INSERT INTO addresses 
    (hash, number, street, unit, city, district, region, postcode, id, lat, lon)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        number = VALUES(number),
        street = VALUES(street),
        unit = VALUES(unit),
        city = VALUES(city),
        district = VALUES(district),
        region = VALUES(region),
        postcode = VALUES(postcode),
        id = VALUES(id),
        lat = VALUES(lat),
        lon = VALUES(lon)
    """
    keys = ['hash','number','street','unit','city','district','region','postcode','id','lat','lon']
    params_list: List[Tuple] = [tuple(addr.get(k) for k in keys) for addr in addresses]
    dbm = get_db_manager()
    res = dbm.execute_many(insert_query, params_list, database=_geo_db_name())
    if not res.success:
        raise RuntimeError(res.error or 'Batch insert failed')
    return len(addresses)


def load_addresses_from_file(file_path: str, test_rows: Optional[int] = None) -> None:
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist")
        sys.exit(1)

    print(f"Loading addresses from: {file_path}")
    if test_rows:
        print(f"Test mode: Processing only {test_rows} rows")

    batch_size = 1000
    batch: List[Dict[str, Any]] = []
    total_processed = 0
    total_inserted = 0
    start_time = time.time()

    with open(file_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, 1):
            if not line.strip():
                continue
            address_data = parse_geojson_line(line)
            if address_data is None:
                continue
            batch.append(address_data)
            total_processed += 1
            if len(batch) >= batch_size:
                inserted = insert_addresses_batch(batch)
                total_inserted += inserted
                print(f"Processed {total_processed} rows, inserted {total_inserted} addresses")
                batch = []
            if test_rows and total_processed >= test_rows:
                break

    if batch:
        inserted = insert_addresses_batch(batch)
        total_inserted += inserted

    duration = time.time() - start_time
    print("\nLoading complete!")
    print(f"Total processed: {total_processed}")
    print(f"Total inserted: {total_inserted}")
    print(f"Duration: {duration:.2f} seconds")
    if duration > 0:
        print(f"Rate: {total_processed/duration:.0f} rows/second")


def verify_data(limit: int = 10) -> None:
    dbm = get_db_manager()
    res = dbm.execute_query(
        f"""
        SELECT hash, number, street, city, region, postcode, lat, lon 
        FROM addresses 
        ORDER BY hash 
        LIMIT {limit}
        """,
        database=_geo_db_name(),
        fetch=True
    )
    rows = res.data if res.success else []
    print(f"\nSample data verification (first {limit} records):")
    print("-" * 80)
    for row in rows:
        print(f"Hash: {row['hash']}")
        print(f"Address: {row['number']} {row['street']}, {row['city']}, {row['region']} {row['postcode']}")
        print(f"Coordinates: ({row['lat']}, {row['lon']})")
        print("-" * 40)
    res2 = dbm.execute_query("SELECT COUNT(*) as total FROM addresses", database=_geo_db_name(), fetch=True)
    if res2.success and res2.data:
        total = res2.data[0].get('total') or list(res2.data[0].values())[0]
        print(f"Total addresses in database: {total}")
    else:
        print("Total addresses in database: unavailable")


def main():
    parser = argparse.ArgumentParser(description='Load OpenAddresses NDJSON/GeoJSON into MySQL geo database')
    parser.add_argument('file_path', help='Path to the NDJSON/GeoJSON file (one Feature per line recommended)')
    parser.add_argument('--test-rows', type=int, help='Number of rows to process in test mode')
    parser.add_argument('--verify', action='store_true', help='Verify data after loading')
    args = parser.parse_args()

    load_addresses_from_file(args.file_path, args.test_rows)
    if args.verify:
        print("\nVerifying loaded data...")
        verify_data()


if __name__ == '__main__':
    main()



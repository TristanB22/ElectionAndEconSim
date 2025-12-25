#!/usr/bin/env python3
"""
FHFA House Price Index (HPI) Data Fetcher and Inserter

Pulls HPI data from FHFA's public API and inserts it into the database.
Source: https://www.fhfa.gov/hpi/download/monthly/hpi_master.json
"""

from __future__ import annotations

import sys
import json
import requests
from pathlib import Path
from typing import List, Dict, Any


def initialize_paths() -> None:
    """Ensure World_Sim root is on sys.path"""
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def fetch_hpi_data() -> List[Dict[str, Any]]:
    """
    Fetch HPI data from FHFA API.
    
    Returns:
        List of HPI records as dictionaries
    """
    url = "https://www.fhfa.gov/hpi/download/monthly/hpi_master.json"
    
    print(f"Fetching HPI data from {url}...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        print(f"Successfully fetched {len(data):,} HPI records")
        
        return data
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch HPI data: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse JSON response: {e}")
        sys.exit(1)


def main() -> int:
    """Main entry point"""
    initialize_paths()
    
    # Fetch the data
    hpi_data = fetch_hpi_data()

    # Optional CLI mode: if "--print" is supplied, only print first 10
    if any(arg in ("--print", "-p") for arg in sys.argv[1:]):
        print("\n" + "="*80)
        print("First 10 HPI entries:")
        print("="*80 + "\n")
        for i, entry in enumerate(hpi_data[:10], 1):
            print(f"Entry {i}:")
            print(json.dumps(entry, indent=2))
            print()
        return 0

    # Otherwise: truncate and insert into DB
    try:
        from Database.managers.alternative_data import get_alternative_data_manager
        mgr = get_alternative_data_manager()

        print("Truncating world_sim_alternative_data.hpi_data...")
        if not mgr.truncate_hpi():
            print("[ERROR] Failed to truncate hpi_data table")
            return 1

        print(f"Inserting {len(hpi_data):,} rows into hpi_data...")
        if not mgr.insert_hpi_rows(hpi_data):
            print("[ERROR] Failed to insert HPI rows")
            return 1

        print("Done.")
    except Exception as e:
        print(f"[ERROR] Database insert failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


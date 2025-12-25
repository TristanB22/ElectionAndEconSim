#!/usr/bin/env python3
"""
Census ACS Metadata and Data Fetcher/Inserter

Fetches variable metadata and actual census data for ACS Profile, Subject, and 
Housing group endpoints and upserts them into world_sim_census tables.

Usage:
  # Fetch metadata only
  python Utils/gov_data/census_pull_and_insert.py --metadata --years 2024

  # Fetch data only (test mode with first code)
  python Utils/gov_data/census_pull_and_insert.py --data --test --years 2024

  # Fetch both metadata and data with multiprocessing
  python Utils/gov_data/census_pull_and_insert.py --metadata --data --years 2024 --multiprocessing 8

"""

from __future__ import annotations

import os
# Set minimal pool size BEFORE any database imports to prevent connection exhaustion
# This is critical for multiprocessing workers
os.environ['DB_POOL_SIZE'] = '1'
# Skip initializing optional database pools (agents, firms, simulations, geo)
# Census/alternative_data databases will be created on-demand when needed
# This prevents each worker from trying to connect to all databases
os.environ['SKIP_OPTIONAL_DB_POOLS'] = '1'

import sys
import time
import json
import argparse
from typing import Dict, Any, List, Tuple
import multiprocessing
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def initialize_paths() -> None:
    """Ensure World_Sim root is on sys.path (mirrors HPI loader)."""
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def build_census_group_url(year: int, link_type: str, code: str) -> str:
    """
    Construct ACS API group URL based on link_type and code.

    link_type: 'profile' | 'subject' | 'housing'
    code: e.g., 'DP03', 'S1501', 'B08201'
    
    Special case: P1 uses decennial census endpoint (2020 dec cd118 variables)
    """
    # Special override for P1 - uses decennial census endpoint
    if code == 'P1':
        return "https://api.census.gov/data/2020/dec/cd118/variables.json"

    if link_type == 'profile':
        return f"https://api.census.gov/data/{year}/acs/acs1/profile/groups/{code}.json"
    elif link_type == 'subject':
        return f"https://api.census.gov/data/{year}/acs/acs1/subject/groups/{code}.json"
    elif link_type == 'housing':
        return f"https://api.census.gov/data/{year}/acs/acs1/groups/{code}.json"
    else:
        raise ValueError(f"Unsupported link_type: {link_type}")


def build_census_data_url(year: int, link_type: str, code: str) -> str:
    """
    Construct ACS API data URL for county-level data.
    
    Returns URLs like:
    - housing: https://api.census.gov/data/2024/acs/acs1?get=group(B25117)&for=county:*&in=state:*
    - subject: https://api.census.gov/data/2024/acs/acs1/subject?get=group(S1901)&for=county:*&in=state:*
    - profile: https://api.census.gov/data/2024/acs/acs1/profile?get=group(DP04)&for=county:*&in=state:*
    """
    if link_type == 'housing':
        return f"https://api.census.gov/data/{year}/acs/acs1?get=group({code})&for=county:*&in=state:*"
    elif link_type == 'subject':
        return f"https://api.census.gov/data/{year}/acs/acs1/subject?get=group({code})&for=county:*&in=state:*"
    elif link_type == 'profile':
        return f"https://api.census.gov/data/{year}/acs/acs1/profile?get=group({code})&for=county:*&in=state:*"
    else:
        raise ValueError(f"Unsupported link_type for data: {link_type}")


def create_http_session(timeout: int = 30, retries: int = 3, backoff: float = 0.3) -> requests.Session:
    """Create a requests Session with retry strategy."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.request_timeout = timeout
    return session


def fetch_group_metadata(session: requests.Session, url: str, timeout: int) -> Dict[str, Any]:
    """GET the group metadata JSON from Census API; raise on parse errors."""
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception as e:
        # Include a snippet of the body for diagnosis
        snippet = resp.text[:300]
        raise RuntimeError(f"Failed to parse JSON from {url}: {e}; body starts with: {snippet}")


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == 'true'
    return bool(value)


def rows_from_variables(census_code: str, year: int, variables: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert the 'variables' dict from Census into rows for census_columns upsert.
    """
    out: List[Dict[str, Any]] = []
    for var_code, meta in variables.items():
        # Expected fields (provide safe defaults)
        column_label = meta.get('label') or ''
        column_concept = meta.get('concept') or ''
        predicate_type = meta.get('predicateType') or ''
        group_code = meta.get('group') or ''
        limit_value = meta.get('limit') if meta.get('limit') is not None else 0
        try:
            limit_value = int(limit_value)
        except Exception:
            limit_value = 0
        predicate_only = normalize_bool(meta.get('predicateOnly', False))

        out.append({
            'census_code': census_code,
            'year': year,
            'var_code': var_code,
            'column_label': column_label,
            'column_concept': column_concept,
            'predicate_type': predicate_type,
            'group_code': group_code,
            'limit_value': limit_value,
            'predicate_only': predicate_only,
        })
    return out


def parse_census_data_response(
    census_code: str,
    year: int,
    data: List[List[Any]]
) -> List[Dict[str, Any]]:
    """
    Parse Census API data response and extract E (estimate) and M (margin of error) columns.
    
    Args:
        census_code: The census code (e.g., 'B25117')
        year: The year of the data
        data: Raw API response - first row is headers, subsequent rows are data
    
    Returns:
        List of dictionaries ready for census_data upsert
    """
    if not data or len(data) < 2:
        return []
    
    headers = data[0]
    rows = data[1:]
    
    # Find indices for E and M columns, plus geographic identifiers
    e_columns = {}  # {var_base: (e_idx, m_idx)}
    geo_id_idx = None
    name_idx = None
    state_idx = None
    county_idx = None
    
    for idx, header in enumerate(headers):
        if header == 'GEO_ID':
            geo_id_idx = idx
        elif header == 'NAME':
            name_idx = idx
        elif header == 'state':
            state_idx = idx
        elif header == 'county':
            county_idx = idx
        elif header.endswith('E'):
            # This is an estimate column
            var_base = header[:-1]  # Remove 'E' suffix
            if var_base not in e_columns:
                e_columns[var_base] = {'e_idx': idx, 'm_idx': None}
            else:
                e_columns[var_base]['e_idx'] = idx
        elif header.endswith('M'):
            # This is a margin of error column
            var_base = header[:-1]  # Remove 'M' suffix
            if var_base not in e_columns:
                e_columns[var_base] = {'e_idx': None, 'm_idx': idx}
            else:
                e_columns[var_base]['m_idx'] = idx
    
    # Verify we have required geographic columns
    if geo_id_idx is None or name_idx is None or state_idx is None or county_idx is None:
        raise ValueError(
            f"Missing required geographic columns: GEO_ID={geo_id_idx}, "
            f"NAME={name_idx}, state={state_idx}, county={county_idx}"
        )
    
    # Transform data rows
    result = []
    for row in rows:
        if not row or len(row) <= max(geo_id_idx, name_idx, state_idx, county_idx):
            continue
        
        geo_id = row[geo_id_idx]
        geo_name = row[name_idx]
        geo_state = row[state_idx]
        geo_county = row[county_idx]
        
        # Skip rows with null geographic identifiers
        if not geo_id or not geo_name or not geo_state or not geo_county:
            continue
        
        # Extract E and M values for each variable
        for var_base, indices in e_columns.items():
            e_idx = indices.get('e_idx')
            m_idx = indices.get('m_idx')
            
            # Only process if we have both E and M columns
            if e_idx is None or m_idx is None:
                continue
            
            if e_idx >= len(row) or m_idx >= len(row):
                continue
            
            e_val = row[e_idx]
            m_val = row[m_idx]
            
            # Parse numeric values, filtering sentinel values (< -1,000,000)
            try:
                if e_val is None or e_val == '' or e_val == 'null':
                    estimated_value = None
                else:
                    estimated_value = float(e_val)
                    if estimated_value < -1000000:
                        estimated_value = None
            except (ValueError, TypeError):
                estimated_value = None
            
            try:
                if m_val is None or m_val == '' or m_val == 'null':
                    moe = None
                else:
                    moe = float(m_val)
                    if moe < -1000000:
                        moe = None
            except (ValueError, TypeError):
                moe = None
            
            # Create database row
            result.append({
                'census_code': census_code,
                'year': year,
                'var_code': f"{var_base}E",  # Store with E suffix to match census_columns
                'geo_id': geo_id,
                'geo_name': geo_name,
                'geo_state': geo_state,
                'geo_county': geo_county,
                'estimated_value': estimated_value if estimated_value is not None else 0,
                'moe': moe if moe is not None else 0,
            })
    
    return result


def _worker_process_metadata(args_tuple: Tuple[int, Dict[str, Any], bool]) -> Tuple[str, int, int, str]:
    """
    Worker to fetch, transform, and upsert metadata for one (year, code) task.
    Returns: (code, year, rows_upserted, error_message)
    """
    year, row, verbose = args_tuple
    try:
        # Late import in worker to ensure sys.path is set in each process
        initialize_paths()
        from Database.managers.alternative_data import get_alternative_data_manager

        code = row.get('code')
        link_type = row.get('link_type')
        if not code or not link_type:
            return (str(code), year, 0, "Missing code/link_type")

        # P1 decennial special-case: only process once per run; parent filters duplicates
        url = build_census_group_url(year, link_type, code)
        session = create_http_session()
        timeout = getattr(session, 'request_timeout', 30)

        payload = fetch_group_metadata(session, url, timeout)
        variables = payload.get('variables') or {}
        if not isinstance(variables, dict) or not variables:
            return (code, year, 0, "No variables in payload")

        upsert_rows = rows_from_variables(code, year, variables)
        # Filter overly long concepts
        upsert_rows = [r for r in upsert_rows if len(str(r.get('column_concept', ''))) <= 1000]

        mgr = get_alternative_data_manager()
        ok, error_msg = mgr.upsert_census_metadata(upsert_rows)
        if not ok:
            return (code, year, 0, error_msg or "Upsert failed")
        return (code, year, len(upsert_rows), "")
    except Exception as e:
        return (str(row.get('code')), year, 0, f"{type(e).__name__}: {e}")


def _worker_process_data(args_tuple: Tuple[int, Dict[str, Any], bool]) -> Tuple[str, int, int, str]:
    """
    Worker to fetch, transform, and upsert census data for one (year, code) task.
    Returns: (code, year, rows_upserted, error_message)
    """
    year, row, verbose = args_tuple
    try:
        # Late import in worker to ensure sys.path is set in each process
        initialize_paths()
        from Database.managers.alternative_data import get_alternative_data_manager

        code = row.get('code')
        link_type = row.get('link_type')
        if not code or not link_type:
            return (str(code), year, 0, "Missing code/link_type")

        url = build_census_data_url(year, link_type, code)
        session = create_http_session()
        timeout = getattr(session, 'request_timeout', 30)

        # Fetch data (returns array of arrays)
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        
        if not isinstance(data, list) or len(data) < 2:
            return (code, year, 0, "No data rows in response")

        # Parse and transform data
        upsert_rows = parse_census_data_response(code, year, data)
        
        if not upsert_rows:
            return (code, year, 0, "No valid rows after parsing")

        # Upsert to database
        mgr = get_alternative_data_manager()
        ok, error_msg = mgr.upsert_census_data_rows(upsert_rows)
        if not ok:
            return (code, year, 0, error_msg or "Upsert failed")
        
        return (code, year, len(upsert_rows), "")
    except Exception as e:
        return (str(row.get('code')), year, 0, f"{type(e).__name__}: {e}")


def handle_metadata(years: List[int], verbose: bool = True, mp_workers: int = None) -> int:
    """
    Fetch metadata for all rows in code_to_db for each requested year and upsert
    into world_sim_census.census_columns.
    """
    from Database.managers.alternative_data import get_alternative_data_manager

    mgr = get_alternative_data_manager()
    codes = mgr.get_census_code_rows()
    if verbose:
        print(f"Found {len(codes)} census code rows in world_sim_census.code_to_db")

    total_rows_upserted = 0
    # Default years: just 2024 if none specified
    # Also ensure we only process explicitly requested years (no auto-expansion)
    if not years or len(years) == 0:
        years = list(range(2024, 2010 - 1, -1))
    # Track which codes have been processed (for special cases like P1 that ignore year)
    processed_codes = set()
    
    for year in years:
        if verbose:
            print(f"\nProcessing year {year}...")

        # Build task list, skipping duplicate P1 beyond first
        tasks: List[Tuple[int, Dict[str, Any], bool]] = []
        for row in codes:
            code = row.get('code')
            if code == 'P1':
                if code in processed_codes:
                    continue
                processed_codes.add(code)
            tasks.append((year, row, verbose))

        if mp_workers and mp_workers > 0:
            if verbose:
                print(f"  Using {mp_workers} worker processes")
            with multiprocessing.Pool(processes=mp_workers) as pool:
                results = pool.map(_worker_process_metadata, tasks)
        else:
            results = [_worker_process_metadata(t) for t in tasks]

        # Aggregate results
        for code, yr, upserted, err in results:
            if err:
                print(f"  [WARN] {code} for {yr}: {err}")
            else:
                total_rows_upserted += upserted

    if verbose:
        print(f"\nDone. Upserted ~{total_rows_upserted:,} variable rows across {len(years)} year(s).")
    return 0


def handle_data(years: List[int], test_mode: bool = False, verbose: bool = True, mp_workers: int = None) -> int:
    """
    Fetch actual census data for all rows in code_to_db for each requested year and upsert
    into world_sim_census.census_data.
    
    Args:
        years: List of years to process
        test_mode: If True, only process the first code from code_to_db
        verbose: Print progress messages
        mp_workers: Number of multiprocessing workers (None = serial)
    """
    from Database.managers.alternative_data import get_alternative_data_manager

    mgr = get_alternative_data_manager()
    codes = mgr.get_census_code_rows()
    
    if test_mode:
        codes = codes[:1]
        if verbose:
            print(f"[TEST MODE] Processing only first code: {codes[0].get('code') if codes else 'None'}")
    
    if verbose:
        print(f"Found {len(codes)} census code row(s) to process")

    total_rows_upserted = 0
    
    # Default years: just 2024 if none specified
    if not years or len(years) == 0:
        years = list(range(2024, 2010 - 1, -1))
    
    for year in years:
        if verbose:
            print(f"\nProcessing year {year}...")
        
        # Build task list
        tasks: List[Tuple[int, Dict[str, Any], bool]] = []
        for row in codes:
            tasks.append((year, row, verbose))

        if mp_workers and mp_workers > 0:
            if verbose:
                print(f"  Using {mp_workers} worker processes")
            with multiprocessing.Pool(processes=mp_workers) as pool:
                results = pool.map(_worker_process_data, tasks)
        else:
            results = [_worker_process_data(t) for t in tasks]

        # Aggregate results
        for code, yr, upserted, err in results:
            if err:
                print(f"  [WARN] {code} for {yr}: {err}")
            else:
                total_rows_upserted += upserted
                if verbose:
                    print(f"  {code} ({yr}): {upserted:,} rows")

    if verbose:
        print(f"\nDone. Upserted ~{total_rows_upserted:,} data rows across {len(years)} year(s).")
    return 0


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Census ACS metadata and data loader")
    parser.add_argument(
        "--metadata",
        action="store_true",
        help="Fetch variable metadata for codes in world_sim_census.code_to_db and upsert into census_columns",
    )
    parser.add_argument(
        "--data",
        action="store_true",
        help="Fetch actual census data for codes in world_sim_census.code_to_db and upsert into census_data",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: only process the first code from code_to_db (use with --data)",
    )
    parser.add_argument(
        "--years",
        nargs="*",
        type=int,
        help="List of ACS years to query (e.g., 2024 2010). Latest wins on conflicts.",
    )
    parser.add_argument(
        "--multiprocessing",
        nargs='?',
        const=4,
        type=int,
        default=None,
        help="Use N worker processes (default 4 if flag used without N)",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    initialize_paths()
    args = parse_args(argv)

    exit_code = 0
    
    if args.metadata:
        exit_code = handle_metadata(args.years, mp_workers=args.multiprocessing)
        if exit_code != 0:
            return exit_code
    
    if args.data:
        exit_code = handle_data(args.years, test_mode=args.test, mp_workers=args.multiprocessing)
        if exit_code != 0:
            return exit_code
    
    if not args.metadata and not args.data:
        print("Nothing to do. Specify --metadata and/or --data to fetch and insert.")
        return 0
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))



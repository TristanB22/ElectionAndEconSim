#!/usr/bin/env python3
"""
BLS Average Price (AP) Metadata Fetcher and Inserter

Fetches BLS Average Price reference data (areas and items) and inserts into
world_sim_bls tables.

Source:
- Areas: https://download.bls.gov/pub/time.series/ap/ap.area
- Items: https://download.bls.gov/pub/time.series/ap/ap.item

Note: BLS may block automated downloads. If direct download fails, manually
download the files and provide paths using --area-file and --item-file options.

Usage:
  # Fetch and insert metadata (areas, items, series)
  python Utils/gov_data/bls_pull_and_insert.py --metadata

  # Fetch and insert data (monthly values)
  python Utils/gov_data/bls_pull_and_insert.py --data

  # Use local files (recommended if download is blocked)
  python Utils/gov_data/bls_pull_and_insert.py --metadata \\
    --area-file path/to/ap.area \\
    --item-file path/to/ap.item

  # Verbose output
  python Utils/gov_data/bls_pull_and_insert.py --metadata --verbose
"""

from __future__ import annotations

import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# BLS data URLs
BLS_AREA_URL = "https://download.bls.gov/pub/time.series/ap/ap.area"
BLS_ITEM_URL = "https://download.bls.gov/pub/time.series/ap/ap.item"
BLS_SERIES_URL = "https://download.bls.gov/pub/time.series/ap/ap.series"

# Request timeout
REQUEST_TIMEOUT_SECONDS = 30


def initialize_paths() -> None:
    """Ensure World_Sim root is on sys.path."""
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def create_http_session(timeout: int = REQUEST_TIMEOUT_SECONDS) -> requests.Session:
    """
    Create HTTP session with retry logic and timeout.
    
    Args:
        timeout: Request timeout in seconds
        
    Returns:
        Configured requests.Session
    """
    session = requests.Session()
    
    # Set browser-like headers to reduce chance of 403
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Referer': 'https://www.bls.gov/'
    })
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Store timeout on session for later use
    session.request_timeout = timeout
    
    return session


def parse_tsv_data(content: str, skip_header: bool = True) -> List[Dict[str, str]]:
    """
    Parse tab-separated values data into list of dictionaries.
    
    Args:
        content: TSV content as string
        skip_header: Whether to skip the first line (header row)
        
    Returns:
        List of dictionaries with column names as keys
    """
    lines = content.strip().split('\n')
    
    if not lines:
        return []
    
    # First line is the header
    header_line = lines[0]
    headers = [h.strip() for h in header_line.split('\t')]
    
    # Parse data rows
    rows = []
    start_idx = 1 if skip_header else 0
    
    for line in lines[start_idx:]:
        if not line.strip():
            continue
            
        values = line.split('\t')
        
        # Create dictionary mapping headers to values
        row_dict = {}
        for i, header in enumerate(headers):
            value = values[i].strip() if i < len(values) else ""
            row_dict[header] = value
        
        rows.append(row_dict)
    
    return rows


def parse_area_item_from_series_id(series_id: str) -> Tuple[str, str]:
    """Extract area_code (4) and item_code (rest) from series_id like 'APU0000701111'."""
    series_id = (series_id or '').strip()
    if len(series_id) < 10:
        return '', ''
    return series_id[3:7], series_id[7:]


def load_bls_areas_from_file(file_path: str, verbose: bool = False) -> List[Dict[str, str]]:
    """
    Load BLS area reference data from a local file.
    
    Args:
        file_path: Path to local ap.area file
        verbose: Print progress messages
        
    Returns:
        List of area dictionaries with keys: area_code, area_name
    """
    if verbose:
        print(f"Loading BLS areas from {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        rows = parse_tsv_data(content, skip_header=True)
        
        if verbose:
            print(f"  Loaded {len(rows):,} areas")
        
        return rows
        
    except FileNotFoundError:
        print(f"[ERROR] File not found: {file_path}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to load BLS areas from file: {e}")
        return []


def fetch_bls_areas(session: requests.Session, verbose: bool = False) -> List[Dict[str, str]]:
    """
    Fetch BLS area reference data from BLS website.
    
    Args:
        session: HTTP session
        verbose: Print progress messages
        
    Returns:
        List of area dictionaries with keys: area_code, area_name
    """
    if verbose:
        print(f"Fetching BLS areas from {BLS_AREA_URL}...")
    
    start_time = time.perf_counter()
    
    try:
        timeout = getattr(session, 'request_timeout', REQUEST_TIMEOUT_SECONDS)
        # Try HTTPS first
        urls_to_try = [
            BLS_AREA_URL,
            BLS_AREA_URL.replace('https://', 'http://'),
        ]
        last_err = None
        for url in urls_to_try:
            try:
                response = session.get(url, timeout=timeout, allow_redirects=True)
                if response.status_code == 403:
                    last_err = f"403 Forbidden for {url}"
                    continue
                response.raise_for_status()
                content = response.text
                rows = parse_tsv_data(content, skip_header=True)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                if verbose:
                    print(f"  Fetched {len(rows):,} areas in {elapsed_ms:.1f}ms from {url}")
                return rows
            except requests.exceptions.RequestException as inner:
                last_err = str(inner)
                continue
        raise requests.exceptions.RequestException(last_err or "Failed to fetch BLS areas")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch BLS areas: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to parse BLS areas: {e}")
        return []


def load_bls_items_from_file(file_path: str, verbose: bool = False) -> List[Dict[str, str]]:
    """
    Load BLS item reference data from a local file.
    
    Args:
        file_path: Path to local ap.item file
        verbose: Print progress messages
        
    Returns:
        List of item dictionaries with keys: item_code, item_name
    """
    if verbose:
        print(f"Loading BLS items from {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        rows = parse_tsv_data(content, skip_header=True)
        
        if verbose:
            print(f"  Loaded {len(rows):,} items")
        
        return rows
        
    except FileNotFoundError:
        print(f"[ERROR] File not found: {file_path}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to load BLS items from file: {e}")
        return []


def fetch_bls_items(session: requests.Session, verbose: bool = False) -> List[Dict[str, str]]:
    """
    Fetch BLS item reference data from BLS website.
    
    Args:
        session: HTTP session
        verbose: Print progress messages
        
    Returns:
        List of item dictionaries with keys: item_code, item_name
    """
    if verbose:
        print(f"Fetching BLS items from {BLS_ITEM_URL}...")
    
    start_time = time.perf_counter()
    
    try:
        timeout = getattr(session, 'request_timeout', REQUEST_TIMEOUT_SECONDS)
        urls_to_try = [
            BLS_ITEM_URL,
            BLS_ITEM_URL.replace('https://', 'http://'),
        ]
        last_err = None
        for url in urls_to_try:
            try:
                response = session.get(url, timeout=timeout, allow_redirects=True)
                if response.status_code == 403:
                    last_err = f"403 Forbidden for {url}"
                    continue
                response.raise_for_status()
                content = response.text
                rows = parse_tsv_data(content, skip_header=True)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                if verbose:
                    print(f"  Fetched {len(rows):,} items in {elapsed_ms:.1f}ms from {url}")
                return rows
            except requests.exceptions.RequestException as inner:
                last_err = str(inner)
                continue
        raise requests.exceptions.RequestException(last_err or "Failed to fetch BLS items")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch BLS items: {e}")
        return []
def load_bls_series_from_file(file_path: str, verbose: bool = False) -> List[Dict[str, str]]:
    """
    Load BLS series reference data from a local file.
    """
    if verbose:
        print(f"Loading BLS series from {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        rows = parse_tsv_data(content, skip_header=True)
        if verbose:
            print(f"  Loaded {len(rows):,} series")
        return rows
    except FileNotFoundError:
        print(f"[ERROR] File not found: {file_path}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to load BLS series from file: {e}")
        return []


def fetch_bls_series(session: requests.Session, verbose: bool = False) -> List[Dict[str, str]]:
    """
    Fetch BLS series reference data from BLS website.
    """
    if verbose:
        print(f"Fetching BLS series from {BLS_SERIES_URL}...")
    start_time = time.perf_counter()
    try:
        timeout = getattr(session, 'request_timeout', REQUEST_TIMEOUT_SECONDS)
        urls_to_try = [
            BLS_SERIES_URL,
            BLS_SERIES_URL.replace('https://', 'http://'),
        ]
        last_err = None
        for url in urls_to_try:
            try:
                response = session.get(url, timeout=timeout, allow_redirects=True)
                if response.status_code == 403:
                    last_err = f"403 Forbidden for {url}"
                    continue
                response.raise_for_status()
                content = response.text
                rows = parse_tsv_data(content, skip_header=True)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                if verbose:
                    print(f"  Fetched {len(rows):,} series in {elapsed_ms:.1f}ms from {url}")
                return rows
            except requests.exceptions.RequestException as inner:
                last_err = str(inner)
                continue
        raise requests.exceptions.RequestException(last_err or "Failed to fetch BLS series")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch BLS series: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to parse BLS items: {e}")
        return []


def handle_metadata(area_file: str = None, item_file: str = None, series_file: str = None, verbose: bool = True) -> int:
    """
    Fetch BLS reference data (areas and items) and upsert into database.
    
    Args:
        area_file: Path to local ap.area file (if provided, skips download)
        item_file: Path to local ap.item file (if provided, skips download)
        verbose: Print progress messages
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    from Database.managers.alternative_data import get_alternative_data_manager
    
    if verbose:
        print("=" * 80)
        print("BLS Average Price Metadata Fetch and Insert")
        print("=" * 80)
        print()
    
    mgr = get_alternative_data_manager()
    session = create_http_session()
    
    total_errors = 0
    
    # Clear and insert areas
    if verbose:
        print("Step 1: Clearing and loading BLS areas...")
    try:
        mgr.truncate_bls_ap_area()
        if verbose:
            print("  Cleared world_sim_bls.ap_area")
    except Exception as e:
        print(f"  [WARN] Failed to clear ap_area: {e}")
    
    if area_file:
        areas = load_bls_areas_from_file(area_file, verbose=verbose)
    else:
        areas = fetch_bls_areas(session, verbose=verbose)
    
    if areas:
        if verbose:
            print(f"  Upserting {len(areas):,} areas into world_sim_bls.ap_area...")
        
        success, error_msg = mgr.upsert_bls_areas(areas)
        
        if success:
            if verbose:
        else:
            print(f"  ✗ Failed to upsert areas: {error_msg}")
            total_errors += 1
    else:
        print("  [WARN] No areas fetched")
        total_errors += 1
    
    if verbose:
        print()
    
    # Clear and insert items
    if verbose:
        print("Step 2: Clearing and loading BLS items...")
    try:
        mgr.truncate_bls_ap_item()
        if verbose:
            print("  Cleared world_sim_bls.ap_item")
    except Exception as e:
        print(f"  [WARN] Failed to clear ap_item: {e}")
    
    if item_file:
        items = load_bls_items_from_file(item_file, verbose=verbose)
    else:
        items = fetch_bls_items(session, verbose=verbose)
    
    if items:
        if verbose:
            print(f"  Upserting {len(items):,} items into world_sim_bls.ap_item...")
        
        success, error_msg = mgr.upsert_bls_items(items)
        
        if success:
            if verbose:
        else:
            print(f"  ✗ Failed to upsert items: {error_msg}")
            total_errors += 1
    else:
        print("  [WARN] No items fetched")
        total_errors += 1
    
    if verbose:
        print()
    
    # Clear and insert series
    if verbose:
        print("Step 3: Clearing and loading BLS series...")
    try:
        mgr.truncate_bls_ap_series()
        if verbose:
            print("  Cleared world_sim_bls.ap_series")
    except Exception as e:
        print(f"  [WARN] Failed to clear ap_series: {e}")

    if series_file:
        series_rows = load_bls_series_from_file(series_file, verbose=verbose)
    else:
        series_rows = fetch_bls_series(session, verbose=verbose)
    
    if series_rows:
        if verbose:
            print(f"  Upserting {len(series_rows):,} series into world_sim_bls.ap_series...")
        success, error_msg = mgr.upsert_bls_series(series_rows)
        if success:
            if verbose:
        else:
            print(f"  ✗ Failed to upsert series: {error_msg}")
            total_errors += 1
    else:
        print("  [WARN] No series fetched")
        total_errors += 1

    if verbose:
        print()
        print("=" * 80)
        if total_errors == 0:
        else:
            print(f"✗ Completed with {total_errors} error(s)")
        print("=" * 80)
    
    return 1 if total_errors > 0 else 0


def handle_data(verbose: bool = True) -> int:
    """
    Fetch BLS AP data files and upsert into world_sim_bls.ap_data.
    Sources include:
      - https://download.bls.gov/pub/time.series/ap/ap.data.3.Food
      - https://download.bls.gov/pub/time.series/ap/ap.data.2.Gasoline
      - https://download.bls.gov/pub/time.series/ap/ap.data.1.HouseholdFuels
    """
    from Database.managers.alternative_data import get_alternative_data_manager
    
    if verbose:
        print("=" * 80)
        print("BLS Average Price DATA Fetch and Insert")
        print("=" * 80)
        print()
    
    mgr = get_alternative_data_manager()
    session = create_http_session()
    
    # Clear target table
    if verbose:
        print("Step 1: Clearing world_sim_bls.ap_data...")
    try:
        mgr.truncate_bls_ap_data()
        if verbose:
            print("  Cleared world_sim_bls.ap_data")
    except Exception as e:
        print(f"  [WARN] Failed to clear ap_data: {e}")
    
    # Data URLs to pull (can be extended)
    data_urls = [
        "https://download.bls.gov/pub/time.series/ap/ap.data.3.Food",
        "https://download.bls.gov/pub/time.series/ap/ap.data.2.Gasoline",
        "https://download.bls.gov/pub/time.series/ap/ap.data.1.HouseholdFuels",
    ]
    
    all_rows: List[Dict[str, any]] = []
    
    def fetch_url(url: str) -> List[Dict[str, str]]:
        if verbose:
            print(f"Fetching {url} ...")
        start = time.perf_counter()
        timeout = getattr(session, 'request_timeout', REQUEST_TIMEOUT_SECONDS)
        urls_to_try = [url, url.replace('https://', 'http://')]
        last_err = None
        for u in urls_to_try:
            try:
                resp = session.get(u, timeout=timeout, allow_redirects=True)
                if resp.status_code == 403:
                    last_err = f"403 Forbidden for {u}"
                    continue
                resp.raise_for_status()
                rows = parse_tsv_data(resp.text, skip_header=True)
                if verbose:
                    elapsed = (time.perf_counter() - start) * 1000
                    print(f"  Fetched {len(rows):,} rows in {elapsed:.1f}ms from {u}")
                return rows
            except requests.exceptions.RequestException as inner:
                last_err = str(inner)
                continue
        print(f"  [ERROR] Failed to fetch {url}: {last_err}")
        return []
    
    # Fetch each file and transform to ap_data schema
    for url in data_urls:
        rows = fetch_url(url)
        for r in rows:
            series_id = r.get('series_id') or r.get('series id') or ''
            year = r.get('year')
            period = r.get('period')
            value_raw = (r.get('value') or '').strip()
            footnotes = r.get('footnote_codes') or r.get('footnotes') or ''
            
            # Skip rows with non-numeric or missing values
            if value_raw in ('', 'NA', '.', '-'):
                continue
            try:
                value = float(value_raw)
            except ValueError:
                continue
            
            area_code, item_code = parse_area_item_from_series_id(series_id)
            if not area_code or not item_code:
                continue
            
            all_rows.append({
                'series_id': series_id,
                'area_code': area_code,
                'item_code': item_code,
                'year': year,
                'period': period,
                'value': value,
                'footnotes': footnotes,
            })
    
    if verbose:
        print()
        print(f"Step 2: Upserting {len(all_rows):,} data rows into world_sim_bls.ap_data...")
    ok, err = mgr.upsert_bls_ap_data(all_rows)
    if not ok:
        print(f"  ✗ Failed to upsert ap_data: {err}")
        return 1
    if verbose:
        print("=" * 80)
        print("=" * 80)
    return 0


def parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch BLS Average Price metadata and insert into database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch and insert metadata
  python Utils/gov_data/bls_pull_and_insert.py --metadata

  # Verbose output
  python Utils/gov_data/bls_pull_and_insert.py --metadata --verbose
        """
    )
    
    parser.add_argument(
        '--metadata',
        action='store_true',
        help='Fetch and insert BLS reference data (areas and items)'
    )
    parser.add_argument(
        '--data',
        action='store_true',
        help='Fetch and insert BLS data (monthly values)'
    )
    
    parser.add_argument(
        '--area-file',
        type=str,
        help='Path to local ap.area file (skips download if provided)'
    )
    
    parser.add_argument(
        '--item-file',
        type=str,
        help='Path to local ap.item file (skips download if provided)'
    )
    parser.add_argument(
        '--series-file',
        type=str,
        help='Path to local ap.series file (skips download if provided)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print verbose progress messages'
    )
    
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    """Main entry point."""
    initialize_paths()
    args = parse_args(argv)
    
    if not args.metadata and not args.data:
        print("Nothing to do. Specify --metadata and/or --data.")
        return 0
    exit_code = 0
    if args.metadata:
        exit_code = handle_metadata(
            area_file=args.area_file,
            item_file=args.item_file,
            series_file=args.series_file,
            verbose=args.verbose
        )
        if exit_code != 0:
            return exit_code
    if args.data:
        exit_code = handle_data(verbose=args.verbose)
        if exit_code != 0:
            return exit_code
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


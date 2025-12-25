#!/usr/bin/env python3
"""
ACS PUMS Microdata Fetcher (CSV) – Person and Household

Downloads the 1-Year ACS PUMS microdata zip archives for the latest available
year, unzips in-memory, and prints the first 3 lines from each CSV
(`psam_pYY.csv` and `psam_hYY.csv`).

Behavior:
- In normal mode: iterate alphabetically over the 50 states. For the first
  state, try years from current year down to 2010 to find the latest available.
  Record all years that fail during this discovery. For subsequent states,
  skip the failed years and immediately try the best remaining candidates.
  (Note: the PUMS CSVs are national, but the state loop ensures the future
  per-state processing path is exercised while reusing the discovered year.)

- In test mode (`--test`): only try Maine for years [2025, 2024, 2023] in that
  order with a 5-second timeout, and print the first 3 lines from both files
  for the first year that succeeds.

No database writes are performed.
"""

from __future__ import annotations

import sys
import io
import zipfile
import argparse
from typing import List, Tuple, Optional, Dict
from pathlib import Path
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://www2.census.gov/programs-surveys/acs/data/pums/{year}/1-Year/csv_{kind}.zip"
REQUEST_TIMEOUT_SECONDS = 5


STATES_50 = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
]


def initialize_paths() -> None:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def create_http_session(timeout: int = REQUEST_TIMEOUT_SECONDS) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        backoff_factor=0.2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.request_timeout = timeout
    return session


def build_zip_url(year: int, kind: str) -> str:
    return BASE_URL.format(year=year, kind=kind)


def expected_csv_name(year: int, kind: str) -> str:
    yy = str(year % 100).zfill(2)
    return f"psam_{'p' if kind == 'pme' else 'h'}{yy}.csv"


def try_fetch_zip(session: requests.Session, year: int, kind: str, verbose: bool = False) -> Optional[bytes]:
    url = build_zip_url(year, kind)
    if verbose:
        print(f"  Attempting to fetch {year} {kind} from {url}")
    try:
        resp = session.get(url, timeout=getattr(session, 'request_timeout', REQUEST_TIMEOUT_SECONDS))
        if resp.status_code != 200:
            if verbose:
                print(f"    FAILED: HTTP {resp.status_code}")
            return None
        if verbose:
            print(f"    SUCCESS: Got {len(resp.content):,} bytes")
        return resp.content
    except Exception as e:
        if verbose:
            print(f"    FAILED: {type(e).__name__}: {e}")
        return None


def first_n_lines_from_zip_csv(zip_bytes: bytes, csv_name: str, n: int = 3) -> Optional[List[str]]:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            with zf.open(csv_name) as f:
                text = io.TextIOWrapper(f, encoding='utf-8', newline='')
                out: List[str] = []
                for _ in range(n):
                    line = text.readline()
                    if not line:
                        break
                    out.append(line.rstrip('\n'))
                return out
    except Exception:
        return None
    return None


def header_from_zip_csv(zip_bytes: bytes, csv_name: str, expected_year: Optional[int] = None, verbose: bool = False) -> Optional[List[str]]:
    """Extract header row (as list of column names) from a CSV inside a zip."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            all_files = zf.namelist()
            
            # If expected file not found, try to find a matching year file first
            if csv_name not in all_files and expected_year is not None:
                yy = str(expected_year % 100).zfill(2)
                # Priority candidates: exact psam_pYY/psam_hYY
                prioritized_patterns = [
                    f"psam_p{yy}.csv",
                    f"psam_h{yy}.csv",
                    # Older ACS used ssYYpme/ssYYhme naming
                    f"ss{yy}pme.csv",
                    f"ss{yy}hme.csv",
                ]
                chosen = None
                for pat in prioritized_patterns:
                    for f in all_files:
                        if f.lower() == pat.lower():
                            chosen = f
                            break
                    if chosen:
                        break
                if chosen:
                    csv_name = chosen
                    if verbose:
                        print(f"    Using year-matched file: {csv_name}")
                else:
                    # Fall back to any plausible CSV inside (prefer psam*, then ss*me/hme)
                    candidates = [f for f in all_files if f.lower().endswith('.csv') and ('psam' in f.lower() or f.lower().startswith('ss'))]
                    if candidates:
                        csv_name = candidates[0]
                        if verbose:
                            print(f"    WARNING: Expected file for year {expected_year} not found")
                            print(f"    Files in zip: {', '.join(all_files[:5])}")
                            if len(all_files) > 5:
                                print(f"    ... and {len(all_files) - 5} more files")
                            print(f"    Using fallback file: {csv_name}")
                    else:
                        if verbose:
                            print(f"    WARNING: Expected {csv_name} not found in zip")
                            print(f"    Files in zip: {', '.join(all_files)}")
                        return None
            elif csv_name not in all_files:
                # No expected year provided, just try to find any psam CSV
                candidates = [f for f in all_files if f.lower().endswith('.csv') and ('psam' in f.lower() or f.lower().startswith('ss'))]
                if candidates:
                    csv_name = candidates[0]
                    if verbose:
                        print(f"    Using found CSV file: {csv_name}")
                else:
                    if verbose:
                        print(f"    WARNING: Expected {csv_name} not found in zip")
                        print(f"    Files in zip: {', '.join(all_files)}")
                    return None
            
            with zf.open(csv_name) as f:
                text = io.TextIOWrapper(f, encoding='utf-8', newline='')
                first_line = text.readline()
                if not first_line:
                    return None
                reader = io.StringIO(first_line)
                import csv as _csv
                return next(_csv.reader(reader))
    except Exception as e:
        if verbose:
            print(f"    Exception extracting header: {type(e).__name__}: {e}")
        return None
    return None


def resolve_csv_name_in_zip(zip_bytes: bytes, csv_name: str, expected_year: Optional[int], kind: str, verbose: bool = False) -> Optional[str]:
    """Resolve the actual CSV filename inside the zip for the given year/kind."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            all_files = zf.namelist()
            if csv_name in all_files:
                return csv_name
            yy = str(expected_year % 100).zfill(2) if expected_year is not None else None
            # Determine patterns based on kind
            if kind == 'pme':
                primary_patterns = [
                    f"psam_p{yy}.csv" if yy else None,
                    f"ss{yy}pme.csv" if yy else None,
                ]
            else:
                primary_patterns = [
                    f"psam_h{yy}.csv" if yy else None,
                    f"ss{yy}hme.csv" if yy else None,
                ]
            primary_patterns = [p for p in primary_patterns if p]
            for pat in primary_patterns:
                for f in all_files:
                    if f.lower() == pat.lower():
                        return f
            # Fallbacks: any plausible CSV
            candidates = [f for f in all_files if f.lower().endswith('.csv') and ('psam' in f.lower() or f.lower().startswith('ss'))]
            if candidates:
                if verbose:
                    print(f"    WARNING: Using fallback file: {candidates[0]}")
                return candidates[0]
            return None
    except Exception as e:
        if verbose:
            print(f"    Exception resolving csv name: {type(e).__name__}: {e}")
        return None


def header_from_zip_by_name(zip_bytes: bytes, chosen_name: str) -> Optional[List[str]]:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            with zf.open(chosen_name) as f:
                text = io.TextIOWrapper(f, encoding='utf-8', newline='')
                first_line = text.readline()
                if not first_line:
                    return None
                reader = io.StringIO(first_line)
                import csv as _csv
                return next(_csv.reader(reader))
    except Exception:
        return None


def sample_typical_values_from_zip_by_name(zip_bytes: bytes, chosen_name: str, max_rows: int = 200) -> Dict[str, str]:
    """Read up to max_rows and return first non-empty example per column."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            with zf.open(chosen_name) as f:
                import csv as _csv
                text = io.TextIOWrapper(f, encoding='utf-8', newline='')
                reader = _csv.reader(text)
                header = next(reader, None)
                if not header:
                    return {}
                examples: Dict[str, str] = {}
                remaining = set(header)
                for i, row in enumerate(reader):
                    for idx, col in enumerate(header):
                        if col in remaining and idx < len(row):
                            val = row[idx]
                            if isinstance(val, str) and val.strip() == "":
                                continue
                            if val is None:
                                continue
                            examples[col] = val
                            remaining.discard(col)
                    if not remaining or i + 1 >= max_rows:
                        break
                return examples
    except Exception:
        return {}


def collect_headers_across_years(session: requests.Session, candidate_years: List[int], verbose: bool = False) -> Tuple[Dict[int, List[str]], Dict[int, List[str]], Dict[str, str], Dict[str, str]]:
    """
    For each year in candidate_years, attempt to fetch person and household zips
    and extract their CSV headers. Returns two dicts mapping year -> header list
    for person and household, respectively. Only includes years that successfully
    yielded headers for each type independently.
    """
    p_headers_by_year: Dict[int, List[str]] = {}
    h_headers_by_year: Dict[int, List[str]] = {}
    p_examples: Dict[str, str] = {}
    h_examples: Dict[str, str] = {}
    total_years = len(candidate_years)
    print(f"\nScanning {total_years} years ({candidate_years[0]} down to {candidate_years[-1]})...")
    for idx, y in enumerate(candidate_years, 1):
        if verbose:
            print(f"\nYear {idx}/{total_years}: {y}")
        # PERSON
        if verbose:
            print("  [PERSON]")
        p_zip = try_fetch_zip(session, y, 'pme', verbose=verbose)
        if p_zip:
            p_csv = expected_csv_name(y, 'pme')
            if verbose:
                print(f"    Extracting header from {p_csv}")
            chosen = resolve_csv_name_in_zip(p_zip, p_csv, y, 'pme', verbose=verbose)
            if chosen:
                p_hdr = header_from_zip_by_name(p_zip, chosen)
                if p_hdr:
                    p_headers_by_year[y] = p_hdr
                    if verbose:
                        print(f"    Extracted {len(p_hdr)} columns")
                    # sample examples and merge
                    ex = sample_typical_values_from_zip_by_name(p_zip, chosen)
                    for k, v in ex.items():
                        if k not in p_examples:
                            p_examples[k] = v
                else:
                    if verbose:
                        print(f"    FAILED: Could not extract header")
            else:
                if verbose:
                    print("    FAILED: Could not resolve CSV filename in zip")
        else:
            if verbose:
                print("    No person zip available")
        # HOUSEHOLD
        if verbose:
            print("  [HOUSEHOLD]")
        h_zip = try_fetch_zip(session, y, 'hme', verbose=verbose)
        if h_zip:
            h_csv = expected_csv_name(y, 'hme')
            if verbose:
                print(f"    Extracting header from {h_csv}")
            chosen_h = resolve_csv_name_in_zip(h_zip, h_csv, y, 'hme', verbose=verbose)
            if chosen_h:
                h_hdr = header_from_zip_by_name(h_zip, chosen_h)
                if h_hdr:
                    h_headers_by_year[y] = h_hdr
                    if verbose:
                        print(f"    Extracted {len(h_hdr)} columns")
                    ex_h = sample_typical_values_from_zip_by_name(h_zip, chosen_h)
                    for k, v in ex_h.items():
                        if k not in h_examples:
                            h_examples[k] = v
                else:
                    if verbose:
                        print(f"    FAILED: Could not extract header")
            else:
                if verbose:
                    print("    FAILED: Could not resolve CSV filename in zip")
        else:
            if verbose:
                print("    No household zip available")
    
    print(f"\nScan complete: Found {len(p_headers_by_year)} years with person headers, {len(h_headers_by_year)} years with household headers")
    return p_headers_by_year, h_headers_by_year, p_examples, h_examples


def report_missing_columns_by_year(headers_by_year: Dict[int, List[str]]) -> Tuple[List[int], Dict[int, List[str]]]:
    """
    Given a mapping of year -> header list, compute the union of all columns,
    then for each year compute which union columns are missing in that year.
    Returns sorted years and a mapping year -> sorted missing columns.
    """
    total_set = set()
    for cols in headers_by_year.values():
        total_set.update(cols)
    missing_by_year: Dict[int, List[str]] = {}
    for y, cols in headers_by_year.items():
        missing = sorted(total_set.difference(set(cols)))
        missing_by_year[y] = missing
    years_sorted = sorted(headers_by_year.keys(), reverse=True)
    return years_sorted, missing_by_year


def discover_latest_year(session: requests.Session, candidate_years: List[int]) -> Tuple[Optional[int], List[int]]:
    failed_years: List[int] = []
    for y in candidate_years:
        p_zip = try_fetch_zip(session, y, 'pme')
        h_zip = try_fetch_zip(session, y, 'hme')
        if p_zip and h_zip:
            return y, failed_years
        failed_years.append(y)
    return None, failed_years


def process_state(session: requests.Session, state: str, candidate_years: List[int]) -> Tuple[Optional[int], List[str]]:
    chosen_year: Optional[int] = None
    p_lines: List[str] = []
    y = None
    for y in candidate_years:
        p_zip = try_fetch_zip(session, y, 'pme')
        h_zip = try_fetch_zip(session, y, 'hme')
        if not (p_zip and h_zip):
            continue
        p_csv = expected_csv_name(y, 'pme')
        h_csv = expected_csv_name(y, 'hme')
        p_head = first_n_lines_from_zip_csv(p_zip, p_csv, n=3)
        h_head = first_n_lines_from_zip_csv(h_zip, h_csv, n=3)
        if p_head is None or h_head is None:
            continue
        chosen_year = y
        print(f"State: {state} | Year: {y} | Dataset: PERSON ({p_csv})")
        for line in p_head:
            print(line)
        print(f"State: {state} | Year: {y} | Dataset: HOUSEHOLD ({h_csv})")
        for line in h_head:
            print(line)
        break
    return chosen_year, p_lines


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ACS PUMS microdata fetcher (prints first 3 lines)")
    parser.add_argument("--test", action="store_true", help="Test mode: scan Maine back to 2005 and report header differences")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    initialize_paths()
    args = parse_args(argv)

    current_year = datetime.utcnow().year
    if args.test:
        # Test mode: Maine only, scan years back to 2005 with increased timeout and verbose logging
        states = ["Maine"]
        candidate_years = list(range(current_year, 2004, -1))
        timeout = 30  # Longer timeout for test mode to handle older years
        verbose = True
        print("=== TEST MODE: Scanning Maine from 2005 to present ===")
        print(f"Timeout: {timeout} seconds per request")
    else:
        # Normal mode: All states, scan back to 2005
        states = STATES_50
        candidate_years = list(range(current_year, 2005, -1))
        timeout = REQUEST_TIMEOUT_SECONDS
        verbose = False

    session = create_http_session(timeout=timeout)

    failed_years_global: List[int] = []

    # Collect headers across years and report differences per type
    p_headers_by_year, h_headers_by_year, p_examples, h_examples = collect_headers_across_years(session, candidate_years, verbose=verbose)

    # Compute union sets for summary
    p_total_set = set()
    for cols in p_headers_by_year.values():
        p_total_set.update(cols)
    h_total_set = set()
    for cols in h_headers_by_year.values():
        h_total_set.update(cols)

    p_years, p_missing = report_missing_columns_by_year(p_headers_by_year)
    h_years, h_missing = report_missing_columns_by_year(h_headers_by_year)

    print("\n" + "="*80)
    print("=== PERSON (PUMS Person) header differences by year ===")
    print("="*80)
    print(f"Total unique columns across all years: {len(p_total_set)}")
    print(f"Years with successful header extraction: {len(p_years)} ({p_years})")
    print()
    for y in p_years:
        miss = p_missing.get(y, [])
        if miss:
            print(f"{y}: {len(miss)} missing columns out of {len(p_total_set)} total")
            print(f"  Missing: {', '.join(miss)}")
        else:

    print("\n" + "="*80)
    print("=== HOUSEHOLD (PUMS Household) header differences by year ===")
    print("="*80)
    print(f"Total unique columns across all years: {len(h_total_set)}")
    print(f"Years with successful header extraction: {len(h_years)} ({h_years})")
    print()
    for y in h_years:
        miss = h_missing.get(y, [])
        if miss:
            print(f"{y}: {len(miss)} missing columns out of {len(h_total_set)} total")
            print(f"  Missing: {', '.join(miss)}")
        else:

    # Print example value dicts
    print("\n" + "="*80)
    print("=== PERSON (PUMS Person) example values by column ===")
    print("="*80)
    print(p_examples)

    print("\n" + "="*80)
    print("=== HOUSEHOLD (PUMS Household) example values by column ===")
    print("="*80)
    print(h_examples)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))



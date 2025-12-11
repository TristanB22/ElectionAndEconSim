#!/usr/bin/env python3
"""
CBSA ↔ County FIPS Crosswalk Loader

Downloads the CBSA/CSA/FIPS county crosswalk CSV from NBER and upserts it into
world_sim_alternative_data.metro_county_info via the AlternativeData manager.

Source:
  https://data.nber.org/cbsa-csa-fips-county-crosswalk/cbsa2fipsxw.csv

Usage:
  python Utils/gov_data/cbsa_crosswalk_pull_and_insert.py
  python Utils/gov_data/cbsa_crosswalk_pull_and_insert.py --replace  # truncate then load
"""

from __future__ import annotations

import sys
import csv
import io
import argparse
from typing import Dict, Any, List, Tuple
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


CSV_URL = "https://data.nber.org/cbsa-csa-fips-county-crosswalk/cbsa2fipsxw.csv"


def initialize_paths() -> None:
    """Ensure World_Sim root is on sys.path (mirrors other loaders)."""
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


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


def fetch_csv_text(session: requests.Session, url: str, timeout: int) -> str:
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    # NBER serves plain CSV; ensure it's decoded as text
    resp.encoding = resp.encoding or 'utf-8'
    return resp.text


def coerce_int(value: Any) -> int | None:
    """Convert to int or return None for blanks/invalid."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    s = str(value).strip()
    if s == "":
        return None
    try:
        return int(s)
    except Exception:
        return None


def rows_from_csv(csv_text: str) -> List[Dict[str, Any]]:
    """
    Parse CSV text and map to database column names for metro_county_info.

    CSV headers include:
      cbsacode, metropolitandivisioncode, csacode, cbsatitle, metropolitanmicropolitanstatis,
      metropolitandivisiontitle, csatitle, countycountyequivalent, statename, fipsstatecode,
      fipscountycode, centraloutlyingcounty

    DB columns (differences): cbsa_code, cbsa_title vs cbsacode/cbsatitle; others match.
    """
    f = io.StringIO(csv_text)
    reader = csv.DictReader(f)
    out: List[Dict[str, Any]] = []

    for row in reader:
        # Normalize keys (CSV may have varying case or quotes)
        normalized = { (k or "").strip().lower(): (v or "").strip() for k, v in row.items() }

        db_row = {
            'cbsa_code': coerce_int(normalized.get('cbsacode')),
            'metropolitandivisioncode': coerce_int(normalized.get('metropolitandivisioncode')),
            'csacode': coerce_int(normalized.get('csacode')),
            'cbsa_title': normalized.get('cbsatitle', ''),
            'metropolitanmicropolitanstatis': normalized.get('metropolitanmicropolitanstatis', ''),
            'metropolitandivisiontitle': normalized.get('metropolitandivisiontitle', ''),
            'csatitle': normalized.get('csatitle', ''),
            'countycountyequivalent': normalized.get('countycountyequivalent', ''),
            'statename': normalized.get('statename', ''),
            'fipsstatecode': coerce_int(normalized.get('fipsstatecode')),
            'fipscountycode': coerce_int(normalized.get('fipscountycode')),
            'centraloutlyingcounty': normalized.get('centraloutlyingcounty', ''),
        }

        out.append(db_row)

    return out


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CBSA/County crosswalk loader")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Truncate metro_county_info before loading",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    initialize_paths()
    args = parse_args(argv)

    from Database.managers.alternative_data import get_alternative_data_manager

    mgr = get_alternative_data_manager()

    if args.replace:
        ok = mgr.truncate_metro_county_info()
        if not ok:
            print("[ERROR] Failed to truncate world_sim_alternative_data.metro_county_info")
            return 1
        print("Truncated world_sim_alternative_data.metro_county_info")

    session = create_http_session()
    timeout = getattr(session, 'request_timeout', 30)

    print(f"Fetching CBSA crosswalk CSV from {CSV_URL} ...")
    try:
        csv_text = fetch_csv_text(session, CSV_URL, timeout)
    except Exception as e:
        print(f"[ERROR] Failed to fetch CSV: {e}")
        return 1

    rows = rows_from_csv(csv_text)
    print(f"Parsed {len(rows):,} rows. Upserting into metro_county_info ...")

    ok, err = mgr.upsert_metro_county_info(rows)
    if not ok:
        print("[ERROR] Upsert failed:")
        print(err)
        return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))



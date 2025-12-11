#!/usr/bin/env python3
"""
ATUS (American Time Use Survey) multi-year loader and previewer.

- Uses the multi-year ZIP naming pattern like atusresp-0324.zip where 03 is the
  start-year prefix (2003) and 24 is the end-year suffix (2024)
- Discovers the latest available end-year suffix by probing backwards (e.g., 26, 25, 24, ...)
- Keeps each file type's start prefix fixed (e.g., 03/05/11) and applies the discovered end suffix
- Downloads and unzips each ZIP, finds the .dat inside, and prints the first 3 lines

Usage:
  python Utils/gov_data/atus_loader.py --verbose
"""

from __future__ import annotations

import sys
import os
import io
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import zipfile

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
from io import BytesIO, TextIOWrapper


BASE_URL = "https://www.bls.gov/tus/datafiles"

# File types and their fixed start prefixes (two-digit strings)
# 03 -> 2003 start, 05 -> 2005 start, 11 -> 2011 start
FILETYPE_START_PREFIX: Dict[str, str] = {
    "atusact": "03",
    "atuscps": "03",
    "atusresp": "03",
    "atusrost": "03",
    "atussum": "03",
    "atuswgts": "03",
    "atuswho": "03",
    "atuscase": "05",
    "atusrostec": "11",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def create_http_session(timeout: int = 60) -> requests.Session:
    session = requests.Session()
    # Browser-like headers to avoid blocking
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36',
        'Accept': 'application/zip,application/octet-stream,application/*;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.bls.gov/tus/'
    })
    retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"]) 
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.request_timeout = timeout
    return session


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_multi_year_stem(filetype: str, end_suffix: str) -> str:
    """Return the basename without extension, e.g., atusresp-0324.
    Uses the filetype's fixed start prefix combined with the discovered end suffix.
    """
    start_prefix = FILETYPE_START_PREFIX[filetype]
    return f"{filetype}-{start_prefix}{end_suffix}"


def download_zip(session: requests.Session, url: str, dest: Path, verbose: bool = False) -> bool:
    if verbose:
        print(f"Downloading {url} -> {dest}")
    try:
        timeout = getattr(session, 'request_timeout', 60)
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        with open(dest, 'wb') as f:
            f.write(resp.content)
        if verbose:
            print(f"  Saved {dest.stat().st_size:,} bytes")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Download failed: {url} : {e}")
        return False


def unzip_to_dir(zip_path: Path, extract_dir: Path, verbose: bool = False) -> bool:
    if verbose:
        print(f"Unzipping {zip_path.name} -> {extract_dir}")
    try:
        ensure_dir(extract_dir)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
        return True
    except zipfile.BadZipFile as e:
        print(f"[ERROR] Bad zip file {zip_path}: {e}")
        return False


def fetch_zip_bytes(session: requests.Session, url: str, verbose: bool = False) -> Optional[bytes]:
    if verbose:
        print(f"Downloading {url} -> [memory]")
    try:
        timeout = getattr(session, 'request_timeout', 60)
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.content
    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"[ERROR] Download failed: {url} : {e}")
        return None


def extract_dat_first_lines(zip_bytes: bytes, num_lines: int = 3) -> Optional[Tuple[str, List[str]]]:
    try:
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            # Find .dat entries
            dat_members = [zi for zi in zf.infolist() if zi.filename.lower().endswith('.dat')]
            if not dat_members:
                return None
            member = dat_members[0]
            with zf.open(member, 'r') as f:
                text_stream = TextIOWrapper(f, encoding='utf-8', errors='ignore')
                lines: List[str] = []
                for i in range(num_lines):
                    line = text_stream.readline()
                    if not line:
                        break
                    lines.append(line.rstrip())
                return member.filename, lines
    except zipfile.BadZipFile:
        return None
    except Exception:
        return None


def print_first_lines(dat_path: Path, num_lines: int = 3, verbose: bool = False) -> None:
    try:
        with open(dat_path, 'r', encoding='utf-8', errors='ignore') as f:
            print(f"\n{dat_path.name}:")
            for i in range(num_lines):
                line = f.readline()
                if not line:
                    break
                print(f"  Line {i+1}: {line.rstrip()}")
    except Exception as e:
        print(f"[WARN] Failed to read {dat_path}: {e}")


def run(verbose: bool = False) -> int:
    session = create_http_session()
    # Discover latest available end suffix by probing backwards
    current_year = datetime.now().year
    # Start from current year's two-digit suffix and go down (e.g., 25, 24, 23, ...)
    start_suffix = current_year % 100
    discovered_end_suffix: Optional[str] = None

    # Probe with a single representative filetype to avoid redundant failures
    probe_filetype = "atusresp"

    for end in range(start_suffix, 1, -1):
        end_suffix = f"{end:02d}"
        stem = build_multi_year_stem(probe_filetype, end_suffix)
        url = f"{BASE_URL}/{stem}.zip"
        zip_bytes = fetch_zip_bytes(session, url, verbose=verbose)
        if not zip_bytes:
            continue
        extracted = extract_dat_first_lines(zip_bytes, num_lines=1)
        if not extracted:
            continue
        # Found a valid combo; use this suffix for all filetypes
        discovered_end_suffix = end_suffix
        break

    if not discovered_end_suffix:
        print("[ERROR] Unable to discover any available multi-year ZIP set.")
        return 1

    if verbose:
        print(f"\nUsing discovered end suffix: {discovered_end_suffix}")

    # With end suffix discovered, download all filetypes using their start prefixes
    any_success = False
    for ft in FILETYPE_START_PREFIX.keys():
        stem = build_multi_year_stem(ft, discovered_end_suffix)
        url = f"{BASE_URL}/{stem}.zip"
        zip_bytes = fetch_zip_bytes(session, url, verbose=verbose)
        if not zip_bytes:
            continue
        dat_info = extract_dat_first_lines(zip_bytes, num_lines=3)
        if not dat_info:
            continue
        name, lines = dat_info
        any_success = True
        print(f"\n{name}:")
        for idx, line in enumerate(lines, start=1):
            print(f"  Line {idx}: {line}")

    return 0 if any_success else 1


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Discover latest ATUS multi-year ZIP suffix, download all filetypes, unzip, and preview .dat first 3 lines")
    p.add_argument('--verbose', '-v', action='store_true')
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    return run(verbose=args.verbose)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

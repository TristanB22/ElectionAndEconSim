#!/usr/bin/env python3
"""
ATUS (American Time Use Survey) downloader and previewer.

- Downloads ATUS zip files for a given year (default: 2024)
- Unzips each file into its own directory under Data/ATUS/{year}/{basename}
- Finds the only .dat file in each directory
- Prints the first 3 lines of each .dat file

Usage:
  python Utils/gov_data/atus_loader.py --year 2024 --verbose
"""

from __future__ import annotations

import sys
import os
import io
import time
import argparse
from pathlib import Path
from typing import List, Optional
import zipfile

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://www.bls.gov/tus/datafiles"
FILES = [
    "atusact-{}",
    "atuscps-{}",
    "atusresp-{}",
    "atusrost-{}",
    "atusrostec-{}",
    "atussum-{}",
    "atuswgts-{}",
    "atuswho-{}",
]


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


def find_single_dat(extract_dir: Path) -> Optional[Path]:
    dats: List[Path] = [p for p in extract_dir.rglob("*.dat")]
    if len(dats) == 1:
        return dats[0]
    # Prefer a file matching the directory base name
    if dats:
        return dats[0]
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


def run(year: int, verbose: bool = False) -> int:
    session = create_http_session()
    base_out = project_root() / "Data" / "ATUS" / str(year)
    ensure_dir(base_out)

    status_ok = True

    for template in FILES:
        basename = template.format(year)
        url = f"{BASE_URL}/{basename}.zip"
        zip_dest = base_out / f"{basename}.zip"
        out_dir = base_out / basename

        if not download_zip(session, url, zip_dest, verbose=verbose):
            status_ok = False
            continue
        if not unzip_to_dir(zip_dest, out_dir, verbose=verbose):
            status_ok = False
            continue
        dat_file = find_single_dat(out_dir)
        if not dat_file:
            print(f"[WARN] No .dat file found in {out_dir}")
            status_ok = False
            continue
        print_first_lines(dat_file, num_lines=3, verbose=verbose)

    return 0 if status_ok else 1


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download ATUS zips, unzip, and preview .dat first 3 lines")
    p.add_argument('--year', type=int, default=2024)
    p.add_argument('--verbose', '-v', action='store_true')
    return p.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    return run(args.year, verbose=args.verbose)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

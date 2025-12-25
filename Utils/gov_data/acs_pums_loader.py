#!/usr/bin/env python3
"""
ACS PUMS Data Loader (Housing and Person)

Downloads ACS PUMS microdata CSVs for specified years, harmonizes column names
per the integration guide, validates no conflicting duplicates exist, and
inserts into world_sim_census.pums_h (and eventually pums_p).

Harmonization rules:
- ADJINC vs ADJUST → ADJINC
- TYPEHUGQ vs TYPE → TYPEHUGQ
- BDSP vs BDS → BDSP
- RMSP vs RMS → RMSP
- VALP vs VAL → VALP
- STATE vs ST → ST
- WGTP1..80 (uppercase) vs wgtp1..80 (lowercase) → uppercase
- Year-dependent fields (BROADBND, SMARTPHONE, etc.) → NULL if not present

Usage:
  python Utils/gov_data/acs_pums_loader.py --housing  # Default: current year through 2005
  python Utils/gov_data/acs_pums_loader.py --housing --years 2023 2022 2021  # Specific years
  python Utils/gov_data/acs_pums_loader.py --housing --test  # Test mode: 2023 only
  python Utils/gov_data/acs_pums_loader.py --housing --replace  # Truncate first, then load all
"""

from __future__ import annotations

import sys
import os
# Set a small default pool size to avoid MySQL connection exhaustion
# Can be overridden with DB_POOL_SIZE environment variable
if 'DB_POOL_SIZE' not in os.environ:
    os.environ['DB_POOL_SIZE'] = '2'

import io
import zipfile
import argparse
import csv as _csv
import json
import re
import multiprocessing
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://www2.census.gov/programs-surveys/acs/data/pums/{year}/1-Year/csv_{kind}.zip"
REQUEST_TIMEOUT_SECONDS = 30


def initialize_paths() -> None:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def create_http_session(timeout: int = REQUEST_TIMEOUT_SECONDS) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.3,
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
    if kind == 'hme':
        return f"psam_h{yy}.csv"
    else:
        return f"psam_p{yy}.csv"


def try_fetch_zip(session: requests.Session, year: int, kind: str, verbose: bool = False) -> Optional[bytes]:
    url = build_zip_url(year, kind)
    if verbose:
        print(f"  Fetching {url}")
    try:
        resp = session.get(url, timeout=getattr(session, 'request_timeout', REQUEST_TIMEOUT_SECONDS))
        if resp.status_code != 200:
            if verbose:
                print(f"    HTTP {resp.status_code}")
            return None
        if verbose:
            print(f"    Got {len(resp.content):,} bytes")
        return resp.content
    except Exception as e:
        if verbose:
            print(f"    Exception: {type(e).__name__}: {e}")
        return None


def resolve_csv_name_in_zip(zip_bytes: bytes, expected_name: str, year: int, kind: str, verbose: bool = False) -> Optional[str]:
    """Find the actual CSV filename inside the zip for the given year/kind."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            all_files = zf.namelist()
            if expected_name in all_files:
                return expected_name
            
            yy = str(year % 100).zfill(2)
            # Try alternate patterns
            if kind == 'hme':
                patterns = [f"psam_h{yy}.csv", f"ss{yy}hme.csv"]
            else:
                patterns = [f"psam_p{yy}.csv", f"ss{yy}pme.csv"]
            
            for pat in patterns:
                for f in all_files:
                    if f.lower() == pat.lower():
                        if verbose:
                            print(f"    Resolved to {f}")
                        return f
            
            # Fallback: any CSV with psam or ss
            candidates = [f for f in all_files if f.lower().endswith('.csv') and ('psam' in f.lower() or f.lower().startswith('ss'))]
            if candidates:
                if verbose:
                    print(f"    Using fallback: {candidates[0]}")
                return candidates[0]
            return None
    except Exception as e:
        if verbose:
            print(f"    Exception resolving CSV name: {type(e).__name__}: {e}")
        return None


def read_csv_from_zip(zip_bytes: bytes, csv_name: str) -> List[Dict[str, str]]:
    """Read all rows from a CSV inside a zip as list of dicts."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            with zf.open(csv_name) as f:
                text = io.TextIOWrapper(f, encoding='utf-8', newline='')
                reader = _csv.DictReader(text)
                return list(reader)
    except Exception as e:
        print(f"    ERROR reading CSV {csv_name}: {type(e).__name__}: {e}")
        return []


# ============================================================================
# Harmonization logic per integration guide
# ============================================================================

class HarmonizationError(Exception):
    """Raised when conflicting duplicate columns are found."""
    pass


class ConversionError(Exception):
    """Raised when a value cannot be converted to the expected type."""
    pass


# Fields that should remain as strings (not converted to int)
HOUSING_TEXT_FIELDS = {'RT', 'SERIALNO', 'DIVISION', 'PUMA', 'REGION', 'ADJHSG', 'ADJINC', 'TYPEHUGQ', 'FS', 'FFSP'}
PERSON_TEXT_FIELDS = {'RT', 'SERIALNO', 'SPORDER', 'DIVISION', 'PUMA', 'REGION', 'STATE', 'ADJINC', 'NAICSP', 'SOCP'}


def safe_int_convert(value: Any, field_name: str, allow_empty: bool = True) -> int:
    """
    Safely convert a value to integer, raising ConversionError if conversion fails.
    Leading zeros are automatically handled (converted to int).
    
    Args:
        value: The value to convert
        field_name: Name of the field (for error messages)
        allow_empty: If True, empty/None values become 0. If False, raises error.
    
    Returns:
        Integer value
        
    Raises:
        ConversionError if conversion fails (only for non-numeric values)
    """
    # Handle None and empty strings (including whitespace-only)
    if value is None:
        if allow_empty:
            return 0
        else:
            raise ConversionError(f"Field {field_name} cannot be empty (required)")
    
    val_str = str(value).strip()
    
    # Check if it's empty after stripping
    if val_str == '':
        if allow_empty:
            return 0
        else:
            raise ConversionError(f"Field {field_name} cannot be empty (required)")
    
    # Try to convert (leading zeros are handled automatically by int())
    try:
        return int(val_str)
    except ValueError:
        # Check if it has non-numeric characters
        if not val_str.replace('-', '').replace('+', '').isdigit():
            raise ConversionError(f"Field {field_name} contains non-numeric characters: '{val_str}'")
        raise ConversionError(f"Field {field_name} cannot be converted to integer: '{val_str}'")


def validate_numeric_value(value: Any, field_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a value looks problematic for numeric conversion.
    Only reports non-numeric characters (leading zeros are automatically handled).
    Returns (is_problematic, reason) where reason explains the issue.
    """
    if value is None or value == '':
        return False, None
    
    val_str = str(value).strip()
    
    # If empty after stripping, it's not problematic (will default to 0 or NULL)
    if val_str == '':
        return False, None
    
    # Leading zeros are fine - int() handles them automatically
    # Only check for non-numeric characters
    stripped = val_str.replace('-', '').replace('+', '')
    if not stripped.isdigit():
        return True, f"Non-numeric characters: '{val_str}'"
    
    return False, None


def harmonize_housing_row(raw: Dict[str, str], year: int) -> Dict[str, Any]:
    """
    Transform a raw ACS PUMS housing row into harmonized pums_h schema.
    
    Raises HarmonizationError if conflicting duplicates are detected.
    """
    out: Dict[str, Any] = {}
    
    # 0. Year (context, not in raw)
    out['year'] = year
    
    # 1. Identity fields
    out['RT'] = raw.get('RT')
    out['SERIALNO'] = raw.get('SERIALNO')
    out['DIVISION'] = raw.get('DIVISION')
    out['PUMA'] = raw.get('PUMA')
    out['REGION'] = raw.get('REGION')
    
    # Housing table uses STATE (SMALLINT UNSIGNED)
    state_val = None
    if 'ST' in raw:
        state_val = raw['ST']
    elif 'STATE' in raw:
        state_val = raw['STATE']
    
    if state_val:
        out['STATE'] = safe_int_convert(state_val, 'STATE', allow_empty=False)
    else:
        raise ConversionError("Field STATE cannot be empty (required)")
    
    # 2. Adjustment factors
    # ADJINC vs ADJUST
    if 'ADJINC' in raw and 'ADJUST' in raw:
        # Both present: conflict check
        if raw['ADJINC'] != raw['ADJUST']:
            raise HarmonizationError(f"ADJINC={raw['ADJINC']} != ADJUST={raw['ADJUST']} for SERIALNO={raw.get('SERIALNO')}")
        out['ADJINC'] = raw['ADJINC']
    elif 'ADJINC' in raw:
        out['ADJINC'] = raw['ADJINC']
    elif 'ADJUST' in raw:
        out['ADJINC'] = raw['ADJUST']
    else:
        out['ADJINC'] = '0'
    
    out['ADJHSG'] = raw.get('ADJHSG') or '0'
    
    # 3. Weights (all INT NOT NULL)
    out['WGTP'] = safe_int_convert(raw.get('WGTP'), 'WGTP', allow_empty=False)
    
    # Replicate weights: uppercase WGTP1..80 vs lowercase wgtp1..80
    for i in range(1, 81):
        upper_key = f'WGTP{i}'
        lower_key = f'wgtp{i}'
        val = None
        if upper_key in raw and lower_key in raw:
            # Both present: conflict check
            if raw[upper_key] != raw[lower_key]:
                raise HarmonizationError(f"{upper_key}={raw[upper_key]} != {lower_key}={raw[lower_key]} for SERIALNO={raw.get('SERIALNO')}")
            val = raw[upper_key]
        elif upper_key in raw:
            val = raw[upper_key]
        elif lower_key in raw:
            val = raw[lower_key]
        out[upper_key] = safe_int_convert(val, upper_key, allow_empty=False)
    
    # 4. Household/GQ type: TYPEHUGQ vs TYPE (CHAR field - keep as string)
    if 'TYPEHUGQ' in raw and 'TYPE' in raw:
        # Both present: conflict check
        if raw['TYPEHUGQ'] != raw['TYPE']:
            raise HarmonizationError(f"TYPEHUGQ={raw['TYPEHUGQ']} != TYPE={raw['TYPE']} for SERIALNO={raw.get('SERIALNO')}")
        out['TYPEHUGQ'] = raw['TYPEHUGQ'] if raw['TYPEHUGQ'] else None
    elif 'TYPEHUGQ' in raw:
        out['TYPEHUGQ'] = raw['TYPEHUGQ'] if raw['TYPEHUGQ'] else None
    elif 'TYPE' in raw:
        out['TYPEHUGQ'] = raw['TYPE'] if raw['TYPE'] else None
    else:
        out['TYPEHUGQ'] = None
    
    # 5. Core household counts
    out['NP'] = safe_int_convert(raw.get('NP'), 'NP', allow_empty=False)
    # FS and FFSP are CHAR fields, keep as strings
    out['FS'] = raw.get('FS')
    out['FFSP'] = raw.get('FFSP')
    
    # 6. Big 3 duplicates: BDSP vs BDS, RMSP vs RMS, VALP vs VAL
    # Bedrooms (SMALLINT UNSIGNED NOT NULL) - if empty/missing, use 0
    def get_non_empty(key1, key2=None):
        """Get non-empty value from raw dict, checking key1 first, then key2."""
        val1 = (raw.get(key1) or '').strip()
        if val1:
            return val1
        if key2:
            val2 = (raw.get(key2) or '').strip()
            if val2:
                return val2
        return None
    
    bdsp_val = get_non_empty('BDSP', 'BDS')
    
    # Check for conflict if both present and non-empty
    bdsp_check = (raw.get('BDSP') or '').strip()
    bds_check = (raw.get('BDS') or '').strip()
    if bdsp_check and bds_check and bdsp_check != bds_check:
        raise HarmonizationError(f"BDSP={bdsp_check} != BDS={bds_check} for SERIALNO={raw.get('SERIALNO')}")
    
    out['BDSP'] = safe_int_convert(bdsp_val, 'BDSP', allow_empty=True)  # Allow empty, defaults to 0
    
    # Rooms (SMALLINT UNSIGNED NOT NULL) - if empty/missing, use 0
    rmsp_val = get_non_empty('RMSP', 'RMS')
    
    # Check for conflict if both present and non-empty
    rmsp_check = (raw.get('RMSP') or '').strip()
    rms_check = (raw.get('RMS') or '').strip()
    if rmsp_check and rms_check and rmsp_check != rms_check:
        raise HarmonizationError(f"RMSP={rmsp_check} != RMS={rms_check} for SERIALNO={raw.get('SERIALNO')}")
    
    out['RMSP'] = safe_int_convert(rmsp_val, 'RMSP', allow_empty=True)  # Allow empty, defaults to 0
    
    # Value (INT NOT NULL) - if empty/missing, use 0
    valp_val = get_non_empty('VALP', 'VAL')
    
    # Check for conflict if both present and non-empty
    valp_check = (raw.get('VALP') or '').strip()
    val_check = (raw.get('VAL') or '').strip()
    if valp_check and val_check and valp_check != val_check:
        raise HarmonizationError(f"VALP={valp_check} != VAL={val_check} for SERIALNO={raw.get('SERIALNO')}")
    
    out['VALP'] = safe_int_convert(valp_val, 'VALP', allow_empty=True)  # Allow empty, defaults to 0
    
    # 7. All other housing characteristics: copy 1:1 if present
    # List all columns from pums_h schema (excluding already handled)
    other_cols = [
        'ACCESS', 'ACR', 'AGS', 'BATH', 'BLD', 'BROADBND', 'COMPOTHX', 'CONP',
        'DIALUP', 'ELEP', 'FULP', 'GASP', 'HFL', 'HISPEED', 'HOTWAT', 'INSP',
        'LAPTOP', 'MRGI', 'MRGP', 'MRGT', 'MRGX', 'OTHSVCEX', 'REFR', 'RWAT',
        'RWATPR', 'SATELLITE', 'SINK', 'SMARTPHONE', 'STOV', 'TABLET', 'TEL',
        'TEN', 'VEH', 'WATP', 'YBL', 'FES', 'FINCP', 'FPARC', 'HHL', 'HHLANP',
        'HHT', 'HINCP', 'HUGCL', 'HUPAC', 'HUPAOC', 'HUPARC', 'KIT', 'LNGI',
        'MULTG', 'MV', 'NOC', 'NPF', 'NPP', 'NR', 'NRC', 'OCPIP', 'PARTNER',
        'PLM', 'PLMPRP', 'PSF', 'R18', 'R60', 'R65', 'RESMODE', 'SMOCP', 'SMX',
        'SRNT', 'SSMC', 'SVAL', 'TAXP', 'WIF', 'WKEXREL', 'WORKSTAT',
        # F-allocation flags
        'FACCESSP', 'FACRP', 'FAGSP', 'FBATHP', 'FBDSP', 'FBLDP', 'FBROADBNDP',
        'FCOMPOTHXP', 'FCONP', 'FDIALUPP', 'FELEP', 'FFINCP', 'FFULP', 'FGASP',
        'FGRNTP', 'FHFLP', 'FHINCP', 'FHISPEEDP', 'FHOTWATP', 'FINSP', 'FKITP',
        'FLAPTOPP', 'FMHP', 'FMRGIP', 'FMRGP', 'FMRGTP', 'FMRGXP', 'FMVYP',
        'FOTHSVCEXP', 'FPLMP', 'FPLMPRP', 'FREFRP', 'FRMSP', 'FRNTMP', 'FRNTP',
        'FRWATP', 'FRWATPRP', 'FSATELLITEP', 'FSINKP', 'FSMARTPHONP', 'FSMOCP',
        'FSMP', 'FSMXHP', 'FSMXSP', 'FSTOVP', 'FTABLETP', 'FTAXP', 'FTELP',
        'FTENP', 'FVACSP', 'FVALP', 'FVEHP', 'FWATP', 'FYBLP',
        # Rent/costs
        'RNTM', 'RNTP', 'GRNTP', 'GRPIP', 'VACS', 'MHP', 'SMP',
        # Internet modes
        'BUS', 'TOIL', 'FBUSP', 'FDSLP', 'FFIBEROPP', 'FHANDHELDP', 'FMODEMP',
        'FTOILP', 'HANDHELD', 'DSL', 'FIBEROP', 'MODEM',
        # Late additions
        'SRNTEMP', 'FWIFP', 'FSRNTEMP', 'FFS', 'FFFSP',
    ]
    
    # Fields that are NOT NULL (must have a value) - based on actual schema
    # Only include fields that are actually NOT NULL in 13_census.sql
    housing_not_null_fields = {
        # Identity fields (handled separately but included for completeness)
        'year', 'SERIALNO', 'PUMA', 'STATE', 'ADJHSG', 'ADJINC', 'WGTP', 'NP',
        # Replicate weights (all WGTP1-80 are NOT NULL) - handled separately
        # All other fields (BDSP, RMSP, VALP, BLD, HINCP, etc.) are nullable
    }
    
    # Process all other columns - convert to int if not a text field
    for col in other_cols:
        if col in HOUSING_TEXT_FIELDS:
            # Keep as string
            out[col] = raw.get(col) if raw.get(col) not in (None, '') else None
        else:
            # Convert to int (all other fields are SMALLINT UNSIGNED or INT)
            val = raw.get(col)
            is_required = col in housing_not_null_fields
            try:
                out[col] = safe_int_convert(val, col, allow_empty=not is_required)
            except ConversionError as e:
                # Re-raise with context
                raise ConversionError(f"{e} (SERIALNO={raw.get('SERIALNO')}, year={year})")
    
    return out


def harmonize_person_row(raw: Dict[str, str], year: int) -> Dict[str, Any]:
    """
    Transform a raw ACS PUMS person row into harmonized pums_p schema.
    
    Raises HarmonizationError if conflicting duplicates are detected.
    """
    out: Dict[str, Any] = {}
    
    # 0. Year (context)
    out['year'] = year
    
    # 1. Identity fields
    out['RT'] = raw.get('RT')
    out['SERIALNO'] = raw.get('SERIALNO')
    out['SPORDER'] = raw.get('SPORDER')
    out['DIVISION'] = raw.get('DIVISION')
    out['PUMA'] = raw.get('PUMA')
    out['REGION'] = raw.get('REGION')
    
    # STATE vs ST → prefer ST (CHAR field in pums_p, keep as string)
    if 'ST' in raw:
        out['STATE'] = raw['ST'] if raw['ST'] else None
    elif 'STATE' in raw:
        out['STATE'] = raw['STATE'] if raw['STATE'] else None
    else:
        raise ConversionError(f"Field STATE cannot be empty (required) for SERIALNO={raw.get('SERIALNO')}, SPORDER={raw.get('SPORDER')}")
    
    # 2. Adjustment factors: ADJINC vs ADJUST
    if 'ADJINC' in raw and 'ADJUST' in raw:
        if raw['ADJINC'] != raw['ADJUST']:
            raise HarmonizationError(f"ADJINC={raw['ADJINC']} != ADJUST={raw['ADJUST']} for SERIALNO={raw.get('SERIALNO')}, SPORDER={raw.get('SPORDER')}")
        out['ADJINC'] = raw['ADJINC']
    elif 'ADJINC' in raw:
        out['ADJINC'] = raw['ADJINC']
    elif 'ADJUST' in raw:
        out['ADJINC'] = raw['ADJUST']
    else:
        out['ADJINC'] = '0'
    
    # 3. Weights (all INT)
    out['PWGTP'] = safe_int_convert(raw.get('PWGTP'), 'PWGTP', allow_empty=False)
    
    # Replicate weights: uppercase PWGTP1..80 vs lowercase pwgtp1..80
    for i in range(1, 81):
        upper_key = f'PWGTP{i}'
        lower_key = f'pwgtp{i}'
        val = None
        if upper_key in raw and lower_key in raw:
            if raw[upper_key] != raw[lower_key]:
                raise HarmonizationError(f"{upper_key}={raw[upper_key]} != {lower_key}={raw[lower_key]} for SERIALNO={raw.get('SERIALNO')}, SPORDER={raw.get('SPORDER')}")
            val = raw[upper_key]
        elif upper_key in raw:
            val = raw[upper_key]
        elif lower_key in raw:
            val = raw[lower_key]
        out[upper_key] = safe_int_convert(val, upper_key, allow_empty=False)
    
    # 4. Core demographics
    out['AGEP'] = safe_int_convert(raw.get('AGEP'), 'AGEP', allow_empty=False)
    # SEX, HISP, RAC* are SMALLINT UNSIGNED
    out['SEX'] = safe_int_convert(raw.get('SEX'), 'SEX', allow_empty=False)
    out['HISP'] = safe_int_convert(raw.get('HISP'), 'HISP', allow_empty=False)
    out['RAC1P'] = safe_int_convert(raw.get('RAC1P'), 'RAC1P', allow_empty=False)
    out['RAC2P'] = safe_int_convert(raw.get('RAC2P'), 'RAC2P', allow_empty=False)
    out['RAC3P'] = safe_int_convert(raw.get('RAC3P'), 'RAC3P', allow_empty=False)
    
    # 5. All other person characteristics: copy 1:1 if present
    # List all columns from pums_p schema (excluding already handled)
    other_cols = [
        'RACAIAN', 'RACASN', 'RACBLK', 'RACNH', 'RACNHPI', 'RACNUM', 'RACPI',
        'RACSOR', 'RACWHT', 'WAOB', 'QTRBIR', 'RELP', 'RELSHIPP', 'MSP', 'MAR',
        'MARHD', 'MARHM', 'MARHT', 'MARHW', 'MARHYP', 'ESP', 'NOP',
        # Nativity/migration/citizenship
        'CIT', 'NATIVITY', 'CITWP', 'MIG', 'MIGPUMA', 'MIGSP', 'POBP',
        # Language
        'LANX', 'LANP', 'ENG',
        # Disability
        'DEAR', 'DEYE', 'DOUT', 'DPHY', 'DREM', 'DDRS', 'DIS',
        # Schooling
        'SCH', 'SCHG', 'SCHL', 'FSCHP', 'FSCHGP', 'FSCHLP',
        # Income/earnings (person level) - handle as INT
        'PINCP', 'PERNP', 'WAGP', 'OIP', 'PAP', 'RETP', 'SSIP', 'SSP', 'INTP',
        'SEPM', 'SEMP', 'POVPIP',
        # Health insurance
        'HICOV', 'HIMRKS', 'HINS1', 'HINS2', 'HINS3', 'HINS4', 'HINS5', 'HINS6',
        'HINS7', 'PRIVCOV', 'PUBCOV',
        # Employment/work status
        'ESR', 'COW', 'WRK', 'WKL', 'WKW', 'WKWN', 'WKHP', 'UWRK',
        # Commuting
        'JWTRNS', 'JWTR', 'JWMNP', 'JWRIP', 'JWAP', 'JWDP',
        # Occupation/industry/soc
        'INDP', 'NAICSP', 'OCCP', 'SOCP', 'FOD1P', 'FOD2P', 'SCIENGP', 'SCIENGRLP',
        # Military/veteran
        'MIL', 'VPS',
        # Fertility
        'FER',
        # Mortgage/loan payment flags (person-level)
        'MLPA', 'MLPB', 'MLPCD', 'MLPE', 'MLPFG', 'MLPH', 'MLPIK', 'MLPJ',
        'MLPI', 'MLPK',
        # Disability-related amounts
        'DRAT', 'DRATX',
        # Ancestry
        'ANC', 'ANC1P', 'ANC2P',
        # Year-of-entry/period
        'YOEP', 'DECADE',
        # Place-of-work
        'POWPUMA', 'POWSP',
        # Person-level allocation flags (FxxxP)
        'FAGEP', 'FANCP', 'FCITP', 'FCITWP', 'FCOWP', 'FDDRSP', 'FDEARP',
        'FDEYEP', 'FDISP', 'FDOUTP', 'FDPHYP', 'FDRATP', 'FDRATXP', 'FDREMP',
        'FENGP', 'FESRP', 'FFERP', 'FFODP', 'FGCLP', 'FGCMP', 'FGCRP',
        'FHICOVP', 'FHIMRKSP', 'FHINS1P', 'FHINS2P', 'FHINS3C', 'FHINS3P',
        'FHINS4P', 'FHINS5P', 'FHINS6P', 'FHINS7P', 'FHISP', 'FINDP', 'FINTP',
        'FJWDP', 'FJWMNP', 'FJWRIP', 'FJWTRNSP', 'FLANP', 'FLANXP', 'FMARP',
        'FMARHDP', 'FMARHMP', 'FMARHTP', 'FMARHWP', 'FMARHYP', 'FMIGP', 'FMIGSP',
        'FMILPP', 'FMILSP', 'FOCCP', 'FOIP', 'FPAP', 'FPERNP', 'FPINCP', 'FPOBP',
        'FPOWSP', 'FPRIVCOVP', 'FPUBCOVP', 'FRACP', 'FRELSHIPP', 'FRETP', 'FSEMP',
        'FSEXP', 'FSSIP', 'FSSP', 'FWAGP', 'FWKHP', 'FWKLP', 'FWKWNP', 'FWRKP',
        'FYOEP',
        # Extra person flags
        'GCL', 'GCM', 'GCR', 'OC', 'PAOC', 'RC', 'SSPA', 'DS', 'DWRK', 'FDWRKP',
        'FMILYP', 'MILY', 'SFN', 'SFR',
        # Note: schema includes FHINS3C but not FHINS4C/FHINS5C
    ]
    
    # Fields that are NOT NULL in pums_p schema - based on actual schema
    person_not_null_fields = {
        # Identity fields (handled separately)
        'year', 'SERIALNO', 'SPORDER', 'PUMA', 'STATE', 'ADJINC', 'PWGTP',
        # Replicate weights (all PWGTP1-80 are NOT NULL) - handled separately
        # All other fields (AGEP, SEX, HISP, RELP, PINCP, etc.) are nullable
        # Note: NAICSP, SOCP are CHAR(8) (nullable, text fields, handled separately)
    }
    
    # Process all other columns - convert to int if not a text field
    for col in other_cols:
        if col in PERSON_TEXT_FIELDS:
            # Keep as string
            out[col] = raw.get(col) if raw.get(col) not in (None, '') else None
        else:
            # Convert to int (all other fields are SMALLINT UNSIGNED or INT)
            val = raw.get(col)
            is_required = col in person_not_null_fields
            try:
                out[col] = safe_int_convert(val, col, allow_empty=not is_required)
            except ConversionError as e:
                # Re-raise with context
                raise ConversionError(f"{e} (SERIALNO={raw.get('SERIALNO')}, SPORDER={raw.get('SPORDER')}, year={year})")
    
    return out


def process_housing_year(session: requests.Session, year: int, verbose: bool = False, dry_run: bool = False) -> Tuple[int, int, List[str], Dict[str, List[Tuple[str, str]]]]:
    """
    Fetch housing CSV for a year, harmonize all rows, insert into pums_h.
    
    Returns: (rows_fetched, rows_inserted, errors, problematic_cols)
    """
    if not dry_run:
        from Database.managers.alternative_data import get_alternative_data_manager
        mgr = get_alternative_data_manager()
    else:
        mgr = None
    
    if verbose:
        print(f"\n=== Processing housing year {year} ===")
    
    zip_bytes = try_fetch_zip(session, year, 'hme', verbose=verbose)
    if not zip_bytes:
        return 0, 0, [f"Failed to fetch housing zip for {year}"], {}
    
    csv_name = expected_csv_name(year, 'hme')
    resolved = resolve_csv_name_in_zip(zip_bytes, csv_name, year, 'hme', verbose=verbose)
    if not resolved:
        return 0, 0, [f"Failed to resolve CSV name in zip for {year}"], {}
    
    if verbose:
        print(f"  Reading CSV: {resolved}")
    raw_rows = read_csv_from_zip(zip_bytes, resolved)
    if not raw_rows:
        return 0, 0, [f"No rows read from {resolved} for {year}"], {}
    
    if verbose:
        print(f"  Read {len(raw_rows):,} raw rows. Harmonizing...")
    
    harmonized: List[Dict[str, Any]] = []
    errors: List[str] = []
    problematic_cols: Dict[str, List[Tuple[str, str]]] = {}  # col -> [(raw_value, reason), ...]
    
    for idx, raw in enumerate(raw_rows):
        try:
            h_row = harmonize_housing_row(raw, year)
            harmonized.append(h_row)
        except HarmonizationError as e:
            errors.append(f"Row {idx}: {e}")
        except ConversionError as e:
            # For dry-run, collect problematic values
            if dry_run:
                # Try to extract field name and value from error
                for col in raw.keys():
                    if col in HOUSING_TEXT_FIELDS:
                        continue
                    val = raw.get(col)
                    is_problem, reason = validate_numeric_value(val, col)
                    if is_problem:
                        if col not in problematic_cols:
                            problematic_cols[col] = []
                        if len(problematic_cols[col]) < 5:  # Limit examples
                            problematic_cols[col].append((str(val), reason))
            errors.append(f"Row {idx}: {e}")
            if not dry_run:
                # In non-dry-run mode, fail on conversion errors
                raise
        except Exception as e:
            errors.append(f"Row {idx}: Unexpected error: {type(e).__name__}: {e}")
            if not dry_run:
                raise
    
    if errors:
        if verbose:
            print(f"  {len(errors)} harmonization errors (showing first 5):")
            for err in errors[:5]:
                print(f"    {err}")
        # Continue with successful rows
    
    if not harmonized:
        return len(raw_rows), 0, errors + [f"No rows successfully harmonized for {year}"], problematic_cols
    
    if dry_run:
        # Scan all raw rows for problematic values (silently collect for summary at end)
        for raw in raw_rows:
            for col in raw.keys():
                if col in HOUSING_TEXT_FIELDS:
                    continue
                val = raw.get(col)
                if val and val not in (None, ''):
                    is_problem, reason = validate_numeric_value(val, col)
                    if is_problem:
                        if col not in problematic_cols:
                            problematic_cols[col] = []
                        # Only add if not already seen this value
                        val_str = str(val)
                        if len(problematic_cols[col]) < 5 and not any(v == val_str for v, _ in problematic_cols[col]):
                            problematic_cols[col].append((val_str, reason))
        
        if verbose:
            print(f"  DRY RUN: Would insert {len(harmonized):,} harmonized rows")
            if harmonized:
                print(f"  Sample row keys: {list(harmonized[0].keys())[:10]}...")
        return len(raw_rows), len(harmonized), errors, problematic_cols
    
    if verbose:
        print(f"  Upserting {len(harmonized):,} harmonized rows into pums_h...")
        try:
            sample_keys = sorted(harmonized[0].keys())
            print(f"  Sample columns ({len(sample_keys)}): {sample_keys[:25]} ...")
            print(f"  Contains STATE? {'STATE' in sample_keys}, ST? {'ST' in sample_keys}")
        except Exception:
            pass
    
    # Insert in batches of 1000
    batch_size = 1000
    inserted = 0
    for i in range(0, len(harmonized), batch_size):
        batch = harmonized[i:i+batch_size]
        ok, err_msg = mgr.upsert_pums_h_rows(batch)
        if not ok:
            errors.append(f"Batch {i//batch_size}: {err_msg}")
            if verbose:
                print(f"    Batch {i//batch_size} failed: {err_msg}")
            # Print failing row details and exit so schema can be adjusted
            try:
                m = re.search(r"index (\d+)", err_msg)
                fail_idx = int(m.group(1)) if m else 0
                row = batch[fail_idx]
                col_match = re.search(r"column '([^']+)'", err_msg)
                problem_col = col_match.group(1) if col_match else None
                print("\n==== First failing housing row (for schema debugging) ====")
                print(f"Global batch={i//batch_size}, batch_index={fail_idx}, SERIALNO={row.get('SERIALNO')}, year={row.get('year')}")
                if problem_col:
                    val = row.get(problem_col)
                    print(f"Problem column: {problem_col}, value='{val}', length={len(str(val)) if val is not None else 'None'}")
                # Print compact JSON snapshot (limit very long fields)
                preview = {k: (v if not isinstance(v, str) or len(v) <= 200 else v[:200] + '...') for k, v in row.items()}
                print(json.dumps(preview, indent=2, sort_keys=True))
            except Exception as _e:
                print(f"Could not render failing row snapshot: {_e}")
            sys.exit(2)
        else:
            inserted += len(batch)
            if verbose and (i // batch_size) % 10 == 0:
                print(f"    Inserted {inserted:,}/{len(harmonized):,}")
    
    if verbose:
        print(f"  Done: {inserted:,} rows inserted")
    
    return len(raw_rows), inserted, errors, {}


def process_person_year(session: requests.Session, year: int, verbose: bool = False, dry_run: bool = False) -> Tuple[int, int, List[str], Dict[str, List[Tuple[str, str]]]]:
    """
    Fetch person CSV for a year, harmonize all rows, insert into pums_p.
    
    Returns: (rows_fetched, rows_inserted, errors, problematic_cols)
    """
    errors: List[str] = []
    rows_fetched = 0
    rows_inserted = 0
    
    # Construct URL for person data
    url = f"https://www2.census.gov/programs-surveys/acs/data/pums/{year}/1-Year/csv_pme.zip"
    
    if verbose:
        print(f"  [Person] Fetching {url}...")
    
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        error_msg = f"Failed to fetch person ZIP for {year}: {e}"
        errors.append(error_msg)
        if verbose:
            print(f"    ERROR: {error_msg}")
        return rows_fetched, rows_inserted, errors, {}
    
    # Extract CSV from ZIP
    yy = str(year % 100).zfill(2)
    expected_csv = f"psam_p{yy}.csv"
    
    try:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            all_files = zf.namelist()
            csv_name = expected_csv
            
            # Fallback logic for older file naming
            if csv_name not in all_files:
                # Try ssYYpme.csv pattern
                alt_name = f"ss{yy}pme.csv"
                if alt_name in all_files:
                    csv_name = alt_name
                else:
                    # Find any psam_p*.csv
                    candidates = [f for f in all_files if 'psam_p' in f.lower() and f.endswith('.csv')]
                    if not candidates:
                        # Try ss*pme.csv
                        candidates = [f for f in all_files if 'ss' in f.lower() and 'pme.csv' in f.lower()]
                    if candidates:
                        csv_name = candidates[0]
                        if verbose:
                            print(f"    Using fallback CSV: {csv_name}")
                    else:
                        error_msg = f"Person CSV not found in ZIP for {year}. Files: {all_files}"
                        errors.append(error_msg)
                        if verbose:
                            print(f"    ERROR: {error_msg}")
                        return rows_fetched, rows_inserted, errors, {}
            
            with zf.open(csv_name) as f:
                text_file = io.TextIOWrapper(f, encoding='utf-8', newline='')
                reader = _csv.DictReader(text_file)
                
                # Read all rows first
                raw_rows_list = list(reader)
                
                batch: List[Dict[str, Any]] = []
                batch_size = 1000
                problematic_cols: Dict[str, List[Tuple[str, str]]] = {}
                
                for raw_row in raw_rows_list:
                    rows_fetched += 1
                    
                    try:
                        harmonized = harmonize_person_row(raw_row, year)
                        batch.append(harmonized)
                    except HarmonizationError as e:
                        error_msg = f"Harmonization error for person {year}: {e}"
                        errors.append(error_msg)
                        if verbose:
                            print(f"    ERROR: {error_msg}")
                        continue
                    except ConversionError as e:
                        # For dry-run, collect problematic values
                        if dry_run:
                            for col in raw_row.keys():
                                if col in PERSON_TEXT_FIELDS:
                                    continue
                                val = raw_row.get(col)
                                is_problem, reason = validate_numeric_value(val, col)
                                if is_problem:
                                    if col not in problematic_cols:
                                        problematic_cols[col] = []
                                    if len(problematic_cols[col]) < 5:
                                        val_str = str(val)
                                        if not any(v == val_str for v, _ in problematic_cols[col]):
                                            problematic_cols[col].append((val_str, reason))
                        errors.append(f"Row {rows_fetched}: {e}")
                        if not dry_run:
                            raise
                        continue
                    except Exception as e:
                        error_msg = f"Unexpected error for person row {rows_fetched}: {type(e).__name__}: {e}"
                        errors.append(error_msg)
                        if verbose:
                            print(f"    ERROR: {error_msg}")
                        if not dry_run:
                            raise
                        continue
                    
                    if len(batch) >= batch_size:
                        if not dry_run:
                            from Database.managers.alternative_data import get_alternative_data_manager
                            mgr = get_alternative_data_manager()
                            success, err = mgr.upsert_pums_p_rows(batch)
                            if not success:
                                error_msg = f"Failed to upsert person batch for {year}: {err}"
                                errors.append(error_msg)
                                if verbose:
                                    print(f"    ERROR: {error_msg}")
                                # Print failing row details and exit
                                try:
                                    m = re.search(r"index (\d+)", err)
                                    fail_idx = int(m.group(1)) if m else 0
                                    row = batch[fail_idx]
                                    col_match = re.search(r"column '([^']+)'", err)
                                    problem_col = col_match.group(1) if col_match else None
                                    print("\n==== First failing person row (for schema debugging) ====")
                                    print(f"year={row.get('year')}, SERIALNO={row.get('SERIALNO')}, SPORDER={row.get('SPORDER')}")
                                    if problem_col:
                                        val = row.get(problem_col)
                                        print(f"Problem column: {problem_col}, value='{val}', length={len(str(val)) if val is not None else 'None'}")
                                    preview = {k: (v if not isinstance(v, str) or len(v) <= 200 else v[:200] + '...') for k, v in row.items()}
                                    print(json.dumps(preview, indent=2, sort_keys=True))
                                except Exception as _e:
                                    print(f"Could not render failing person row snapshot: {_e}")
                                sys.exit(2)
                            rows_inserted += len(batch)
                        else:
                            rows_inserted += len(batch)
                        batch = []
                
                # Insert remaining batch or handle dry-run validation
                if dry_run:
                    # Scan all raw rows for problematic values (silently collect for summary at end)
                    for raw_row in raw_rows_list:
                        for col in raw_row.keys():
                            if col in PERSON_TEXT_FIELDS:
                                continue
                            val = raw_row.get(col)
                            if val and val not in (None, ''):
                                is_problem, reason = validate_numeric_value(val, col)
                                if is_problem:
                                    if col not in problematic_cols:
                                        problematic_cols[col] = []
                                    val_str = str(val)
                                    if len(problematic_cols[col]) < 5 and not any(v == val_str for v, _ in problematic_cols[col]):
                                        problematic_cols[col].append((val_str, reason))
                
                # Insert remaining batch
                if batch:
                    if not dry_run:
                        from Database.managers.alternative_data import get_alternative_data_manager
                        mgr = get_alternative_data_manager()
                        success, err = mgr.upsert_pums_p_rows(batch)
                        if not success:
                            error_msg = f"Failed to upsert final person batch for {year}: {err}"
                            errors.append(error_msg)
                            if verbose:
                                print(f"    ERROR: {error_msg}")
                            # Print failing row and exit
                            try:
                                m = re.search(r"index (\d+)", err)
                                fail_idx = int(m.group(1)) if m else 0
                                row = batch[fail_idx]
                                col_match = re.search(r"column '([^']+)'", err)
                                problem_col = col_match.group(1) if col_match else None
                                print("\n==== First failing person row (for schema debugging) ====")
                                print(f"year={row.get('year')}, SERIALNO={row.get('SERIALNO')}, SPORDER={row.get('SPORDER')}")
                                if problem_col:
                                    val = row.get(problem_col)
                                    print(f"Problem column: {problem_col}, value='{val}', length={len(str(val)) if val is not None else 'None'}")
                                preview = {k: (v if not isinstance(v, str) or len(v) <= 200 else v[:200] + '...') for k, v in row.items()}
                                print(json.dumps(preview, indent=2, sort_keys=True))
                            except Exception as _e:
                                print(f"Could not render failing person row snapshot: {_e}")
                            sys.exit(2)
                        rows_inserted += len(batch)
                    else:
                        rows_inserted += len(batch)
    
    except zipfile.BadZipFile as e:
        error_msg = f"Bad ZIP file for person {year}: {e}"
        errors.append(error_msg)
        if verbose:
            print(f"    ERROR: {error_msg}")
        return rows_fetched, rows_inserted, errors, {}
    except Exception as e:
        error_msg = f"Unexpected error processing person {year}: {e}"
        errors.append(error_msg)
        if verbose:
            print(f"    ERROR: {error_msg}")
        return rows_fetched, rows_inserted, errors, {}
    
    if verbose:
        print(f"    [Person] {year}: fetched {rows_fetched} rows, inserted {rows_inserted}")
    
    # Return problematic_cols collected during processing
    # problematic_cols is defined in the processing loop
    if 'problematic_cols' not in locals():
        problematic_cols = {}
    return rows_fetched, rows_inserted, errors, problematic_cols


def process_housing_year_wrapper(args_tuple: Tuple[int, bool, bool]) -> Tuple[int, int, List[str], Dict[str, List[Tuple[str, str]]]]:
    """
    Wrapper function for multiprocessing that unpacks arguments.
    """
    year, verbose, dry_run = args_tuple
    # Create a new session for each worker
    session = create_http_session()
    try:
        return process_housing_year(session, year, verbose=verbose, dry_run=dry_run)
    except Exception as e:
        # Return error information
        error_msg = f"Error processing housing year {year}: {type(e).__name__}: {e}"
        return 0, 0, [error_msg], {}


def process_person_year_wrapper(args_tuple: Tuple[int, bool, bool]) -> Tuple[int, int, List[str], Dict[str, List[Tuple[str, str]]]]:
    """
    Wrapper function for multiprocessing that unpacks arguments.
    """
    year, verbose, dry_run = args_tuple
    # Create a new session for each worker
    session = create_http_session()
    try:
        return process_person_year(session, year, verbose=verbose, dry_run=dry_run)
    except Exception as e:
        # Return error information
        error_msg = f"Error processing person year {year}: {type(e).__name__}: {e}"
        return 0, 0, [error_msg], {}


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ACS PUMS data loader")
    parser.add_argument("--housing", action="store_true", help="Load housing data (pums_h)")
    parser.add_argument("--person", action="store_true", help="Load person data (pums_p)")
    parser.add_argument("--years", nargs="*", type=int, help="Years to load (e.g., 2023 2022 2021). If omitted, defaults to current year through 2005")
    parser.add_argument("--test", action="store_true", help="Test mode: load only 2023")
    parser.add_argument("--replace", action="store_true", help="Truncate table before loading")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and harmonize but don't insert into DB")
    parser.add_argument("--multiprocessing", type=int, default=None, nargs='?', const=16, metavar="N",
                       help="Use N worker processes for parallel processing (default: 16 if --multiprocessing is specified without N, no multiprocessing if flag not provided)")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    initialize_paths()
    args = parse_args(argv)
    
    if not args.housing and not args.person:
        print("Specify --housing and/or --person")
        return 1
    
    if args.test:
        years = [2023]
    elif args.years:
        years = args.years
    else:
        # Default: current year back through 2005
        current_year = datetime.utcnow().year
        years = list(range(current_year, 2004, -1))
        print(f"No years specified. Defaulting to {current_year} down to 2005 ({len(years)} years)")
    
    # Initialize problematic columns collections
    housing_problematic: Dict[str, List[Tuple[str, str]]] = {}
    person_problematic: Dict[str, List[Tuple[str, str]]] = {}
    
    # Determine if we should use multiprocessing
    use_multiprocessing = args.multiprocessing is not None
    num_workers = args.multiprocessing if args.multiprocessing is not None else 1
    
    if args.housing:
        if not args.dry_run:
            from Database.managers.alternative_data import get_alternative_data_manager
            mgr = get_alternative_data_manager()
            
            if args.replace:
                print("Truncating world_sim_census.pums_h...")
                if not mgr.truncate_pums_h():
                    print("Failed to truncate pums_h")
                    return 1
        else:
            print("DRY RUN mode: will not insert into database")
        
        print(f"Loading housing data for years: {years}")
        if use_multiprocessing:
            print(f"Using {num_workers} worker processes")
            # Prepare arguments for multiprocessing
            args_list = [(year, args.verbose, args.dry_run) for year in years]
            with multiprocessing.Pool(processes=num_workers) as pool:
                results = pool.map(process_housing_year_wrapper, args_list)
            
            # Process results
            for year, (fetched, inserted, errors, problematic_cols) in zip(years, results):
                print(f"{year}: fetched={fetched:,}, harmonized={inserted:,}, errors={len(errors)}")
                if errors and not args.verbose:
                    print(f"  First 3 errors: {errors[:3]}")
                # Merge problematic columns across years
                for col, examples in problematic_cols.items():
                    if col not in housing_problematic:
                        housing_problematic[col] = []
                    for val, reason in examples:
                        if len(housing_problematic[col]) < 5 and not any(v == val for v, _ in housing_problematic[col]):
                            housing_problematic[col].append((val, reason))
        else:
            # Serial processing
            session = create_http_session()
            for year in years:
                fetched, inserted, errors, problematic_cols = process_housing_year(session, year, verbose=args.verbose, dry_run=args.dry_run)
                print(f"{year}: fetched={fetched:,}, harmonized={inserted:,}, errors={len(errors)}")
                if errors and not args.verbose:
                    print(f"  First 3 errors: {errors[:3]}")
                # Merge problematic columns across years
                for col, examples in problematic_cols.items():
                    if col not in housing_problematic:
                        housing_problematic[col] = []
                    for val, reason in examples:
                        if len(housing_problematic[col]) < 5 and not any(v == val for v, _ in housing_problematic[col]):
                            housing_problematic[col].append((val, reason))
    
    if args.person:
        if not args.dry_run:
            from Database.managers.alternative_data import get_alternative_data_manager
            mgr = get_alternative_data_manager()
            
            if args.replace:
                print("Truncating world_sim_census.pums_p...")
                if not mgr.truncate_pums_p():
                    print("Failed to truncate pums_p")
                    return 1
        else:
            if not args.housing:  # Only print once if both flags
                print("DRY RUN mode: will not insert into database")
        
        print(f"Loading person data for years: {years}")
        if use_multiprocessing:
            if args.housing:
                print(f"Using {num_workers} worker processes (continuing from housing)")
            # Prepare arguments for multiprocessing
            args_list = [(year, args.verbose, args.dry_run) for year in years]
            with multiprocessing.Pool(processes=num_workers) as pool:
                results = pool.map(process_person_year_wrapper, args_list)
            
            # Process results
            for year, (fetched, inserted, errors, problematic_cols) in zip(years, results):
                print(f"{year}: fetched={fetched:,}, harmonized={inserted:,}, errors={len(errors)}")
                if errors and not args.verbose:
                    print(f"  First 3 errors: {errors[:3]}")
                # Merge problematic columns across years
                for col, examples in problematic_cols.items():
                    if col not in person_problematic:
                        person_problematic[col] = []
                    for val, reason in examples:
                        if len(person_problematic[col]) < 5 and not any(v == val for v, _ in person_problematic[col]):
                            person_problematic[col].append((val, reason))
        else:
            # Serial processing
            session = create_http_session()
            for year in years:
                fetched, inserted, errors, problematic_cols = process_person_year(session, year, verbose=args.verbose, dry_run=args.dry_run)
                print(f"{year}: fetched={fetched:,}, harmonized={inserted:,}, errors={len(errors)}")
                if errors and not args.verbose:
                    print(f"  First 3 errors: {errors[:3]}")
                # Merge problematic columns across years
                for col, examples in problematic_cols.items():
                    if col not in person_problematic:
                        person_problematic[col] = []
                    for val, reason in examples:
                        if len(person_problematic[col]) < 5 and not any(v == val for v, _ in person_problematic[col]):
                            person_problematic[col].append((val, reason))
    
    # Print summary of problematic columns at the end (after all files processed)
    if args.dry_run and (housing_problematic or person_problematic or args.housing or args.person):
        print("\n" + "="*80)
        print("SUMMARY: Problematic columns with non-numeric characters")
        print("="*80)
        
        if args.housing:
            if housing_problematic:
                print("\nHOUSING (pums_h) problematic columns:")
                for col, examples in sorted(housing_problematic.items()):
                    print(f"  {col}:")
                    for val, reason in examples:
                        print(f"    '{val}': {reason}")
            else:
                print("\nHOUSING (pums_h): No problematic columns found")
        
        if args.person:
            if person_problematic:
                print("\nPERSON (pums_p) problematic columns:")
                for col, examples in sorted(person_problematic.items()):
                    print(f"  {col}:")
                    for val, reason in examples:
                        print(f"    '{val}': {reason}")
            else:
                print("\nPERSON (pums_p): No problematic columns found")
        print("="*80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


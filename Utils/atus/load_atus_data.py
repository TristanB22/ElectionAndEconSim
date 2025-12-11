#!/usr/bin/env python3
"""
ATUS Data Loader

Downloads ATUS multi-year ZIP files, extracts .dat files, parses them,
and loads data into world_sim_atus database with proper normalization.
"""

import sys
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
from io import BytesIO, TextIOWrapper
import zipfile
import tempfile
import os
from contextlib import nullcontext
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Utils.gov_data.atus_loader import (
    create_http_session, build_multi_year_stem,
    FILETYPE_START_PREFIX, BASE_URL, fetch_zip_bytes
)
from Database.managers.atus import get_atus_database_manager
from Database.config import get_db_manager
from datetime import datetime

# Get the configured batch size from the central database config
try:
    DB_MANAGER = get_db_manager()
    INSERTION_BATCH_SIZE = DB_MANAGER.get_config().insertion_batch_size
except Exception:
    INSERTION_BATCH_SIZE = 50000 # Fallback

def parse_dat_file(zip_bytes: bytes) -> List[Dict[str, str]]:
    """
    Extract .dat file from ZIP and parse as CSV.
    Returns list of dicts with column names as keys.
    """
    if not zip_bytes:
        return []
    
    try:
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            dat_members = [zi for zi in zf.infolist() if zi.filename.lower().endswith('.dat')]
            if not dat_members:
                return []
            
            member = dat_members[0]
            with zf.open(member, 'r') as f:
                text_stream = TextIOWrapper(f, encoding='utf-8', errors='ignore')
                reader = csv.DictReader(text_stream)
                return list(reader)
    except zipfile.BadZipFile:
        return []
    except Exception as e:
        print(f"[ERROR] Failed to parse dat file: {e}")
        return []


def normalize_value(val: Optional[str], expected_type: str = 'int'):
    """Convert string value to appropriate Python type, handling -1 as None."""
    # Fast path: None or empty string
    if val is None:
        return None
    
    # Only strip once, not multiple times
    val_stripped = val.strip()
    if val_stripped == '' or val_stripped == '-1':
        return None
    
    # Type conversion with fast path for common cases
    if expected_type == 'int':
        try:
            return int(val_stripped)
        except (ValueError, TypeError):
            return None
    elif expected_type == 'float':
        try:
            return float(val_stripped)
        except (ValueError, TypeError):
            return None
    else:  # string
        return val_stripped


def load_case_id_from_atussum(zip_bytes: bytes, verbose: bool = False) -> int:
    """
    Load case_id table from atussum data (demographic columns only).
    Returns number of rows inserted.
    """
    if verbose:
        print("  Loading case_id from atussum...")
    
    if verbose:
        print("    Parsing CSV data...")
    rows_parsed = parse_dat_file(zip_bytes)
    if not rows_parsed:
        print("    [WARN] No data parsed from atussum")
        return 0
    
    if verbose:
        print(f"    Parsed {len(rows_parsed)} rows")
    
    mgr = get_atus_database_manager()
    
    # Extract demographic columns
    if verbose:
        print("    Processing rows...")
    case_id_rows = []
    for idx, row in enumerate(rows_parsed):
        if verbose and idx % 500000 == 0 and idx > 0:
            print(f"      ... processed {idx} rows")
        case_id_rows.append({
            'TUCASEID': row.get('TUCASEID'),
            'GEMETSTA': normalize_value(row.get('GEMETSTA')),
            'GTMETSTA': normalize_value(row.get('GTMETSTA')),
            'PEEDUCA': normalize_value(row.get('PEEDUCA')),
            'PEHSPNON': normalize_value(row.get('PEHSPNON')),
            'PTDTRACE': normalize_value(row.get('PTDTRACE')),
            'TEAGE': normalize_value(row.get('TEAGE')),
            'TELFS': normalize_value(row.get('TELFS')),
            'TEMJOT': normalize_value(row.get('TEMJOT')),
            'TESCHENR': normalize_value(row.get('TESCHENR')),
            'TESCHLVL': normalize_value(row.get('TESCHLVL')),
            'TESEX': normalize_value(row.get('TESEX')),
            'TESPEMPNOT': normalize_value(row.get('TESPEMPNOT')),
            'TRCHILDNUM': normalize_value(row.get('TRCHILDNUM')),
            'TRDPFTPT': normalize_value(row.get('TRDPFTPT')),
            'TRERNWA': normalize_value(row.get('TRERNWA')),
            'TRHOLIDAY': normalize_value(row.get('TRHOLIDAY')),
            'TRSPFTPT': normalize_value(row.get('TRSPFTPT')),
            'TRSPPRES': normalize_value(row.get('TRSPPRES')),
            'TRYHHCHILD': normalize_value(row.get('TRYHHCHILD')),
            'TUDIARYDAY': normalize_value(row.get('TUDIARYDAY')),
            'TUFNWGTP': normalize_value(row.get('TUFNWGTP'), 'float'),
            'TEHRUSLT': normalize_value(row.get('TEHRUSLT')),
            'TUYEAR': normalize_value(row.get('TUYEAR')),
            'TU20FWGT': normalize_value(row.get('TU20FWGT'), 'float'),
        })
    
    # Insert in batches to avoid huge single transaction
    total_inserted = 0
    batch_size = INSERTION_BATCH_SIZE
    pbar = tqdm(total=len(case_id_rows), desc="    Loading case_id", disable=not verbose, unit="rows")
    try:
        for i in range(0, len(case_id_rows), batch_size):
            batch = case_id_rows[i:i+batch_size]
            success, error = mgr.insert_case_id_rows(batch)
            if not success:
                pbar.close()
                print(f"    [ERROR] Batch {i//batch_size + 1}: {error}")
                return total_inserted
            total_inserted += len(batch)
            pbar.update(len(batch))
    finally:
        pbar.close()
    
    if verbose:
    return total_inserted


def load_sum_from_atussum(zip_bytes: bytes, verbose: bool = False) -> int:
    """
    Load sum table from atussum data (activity time columns, normalized).
    Returns number of rows inserted.
    """
    if verbose:
        print("  Loading sum from atussum...")
    
    rows_parsed = parse_dat_file(zip_bytes)
    if not rows_parsed:
        return 0
    
    mgr = get_atus_database_manager()
    
    sum_rows = []
    for row in rows_parsed:
        tucaseid = row.get('TUCASEID')
        # Extract all columns starting with 't' followed by digits (e.g., t010101)
        for col_name, col_value in row.items():
            if col_name.startswith('t') and len(col_name) == 7 and col_name[1:].isdigit():
                minutes = normalize_value(col_value, 'int')
                if minutes is not None and minutes > 0:  # Only store non-zero values
                    sum_rows.append({
                        'TUCASEID': tucaseid,
                        'activity_code': col_name[1:],  # Remove leading 't'
                        'minutes': minutes
                    })
    
    # Insert in batches
    total_inserted = 0
    batch_size = INSERTION_BATCH_SIZE
    pbar = tqdm(total=len(sum_rows), desc="    Loading sum", disable=not verbose, unit="rows")
    try:
        for i in range(0, len(sum_rows), batch_size):
            batch = sum_rows[i:i+batch_size]
            success, error = mgr.insert_sum_rows(batch)
            if not success:
                pbar.close()
                print(f"    [ERROR] Batch {i//batch_size + 1}: {error}")
                return total_inserted
            total_inserted += len(batch)
            pbar.update(len(batch))
    finally:
        pbar.close()
    
    if verbose:
    return total_inserted


def load_weights(zip_bytes: bytes, verbose: bool = False) -> int:
    """
    Load weights table from atuswgts data (wide format).
    Loads in batches to avoid max_allowed_packet errors.
    """
    if verbose:
        print("  Loading weights...")
    
    rows_parsed = parse_dat_file(zip_bytes)
    if not rows_parsed:
        return 0
    
    mgr = get_atus_database_manager()
    
    weight_rows = []
    for row in rows_parsed:
        # Prepare a dictionary for the wide row
        wide_row = {'TUCASEID': row.get('TUCASEID')}
        # Extract TUFNWGTP001..TUFNWGTP160
        for i in range(1, 161):
            col_name = f'TUFNWGTP{i:03d}'
            wide_row[col_name] = normalize_value(row.get(col_name), 'float')
        weight_rows.append(wide_row)
    
    # Insert in much smaller batches (weights table has 161 columns, needs very small batches)
    # 161 columns × 1000 rows = ~161k values per INSERT, which is safer for max_allowed_packet
    total_inserted = 0
    batch_size = max(500, min(1000, INSERTION_BATCH_SIZE // 100))  # Very conservative for 161 columns
    pbar = tqdm(total=len(weight_rows), desc="    Loading weights", disable=not verbose, unit="rows")
    try:
        for i in range(0, len(weight_rows), batch_size):
            batch = weight_rows[i:i+batch_size]
            success, error = mgr.insert_weights_rows(batch)
            if not success:
                pbar.close()
                print(f"    [ERROR] Batch {i//batch_size + 1}: {error}")
                return total_inserted
            total_inserted += len(batch)
            pbar.update(len(batch))
    finally:
        pbar.close()
    
    if verbose:
    return total_inserted


def load_atuscase(zip_bytes: bytes, verbose: bool = False) -> int:
    """Load atuscase table."""
    if verbose:
        print("  Loading atuscase...")
    
    rows_parsed = parse_dat_file(zip_bytes)
    if not rows_parsed:
        return 0
    
    mgr = get_atus_database_manager()
    
    atuscase_rows = []
    for row in rows_parsed:
        atuscase_rows.append({
            'TUCASEID': row.get('TUCASEID'),
            'TR1INTST': normalize_value(row.get('TR1INTST')),
            'TR2INTST': normalize_value(row.get('TR2INTST')),
            'TRFNLOUT': normalize_value(row.get('TRFNLOUT'), 'str'),
            'TRINCEN2': normalize_value(row.get('TRINCEN2')),
            'TUAVGDUR': normalize_value(row.get('TUAVGDUR'), 'float'),
            'TUA_ID': normalize_value(row.get('TUA_ID'), 'str'),
            'TUCPSDP': normalize_value(row.get('TUCPSDP')),
            'TUC_ID': normalize_value(row.get('TUC_ID'), 'str'),
            'TUDQUAL2': normalize_value(row.get('TUDQUAL2')),
            'TUINCENT': normalize_value(row.get('TUINCENT')),
            'TUINTDQUAL': normalize_value(row.get('TUINTDQUAL')),
            'TUINTID': normalize_value(row.get('TUINTID'), 'str'),
            'TUINTRODATE': normalize_value(row.get('TUINTRODATE')),
            'TUINTROPANMONTH': normalize_value(row.get('TUINTROPANMONTH')),
            'TUINTROPANYEAR': normalize_value(row.get('TUINTROPANYEAR')),
            'TULNGSKL': normalize_value(row.get('TULNGSKL')),
            'TUTOTACTNO': normalize_value(row.get('TUTOTACTNO')),
            'TUV_ID': normalize_value(row.get('TUV_ID'), 'str'),
        })
    
    success, error = mgr.insert_atuscase_rows(atuscase_rows)
    if not success:
        print(f"    [ERROR] {error}")
        return 0
    
    if verbose:
    return len(atuscase_rows)


def load_rost(zip_bytes: bytes, verbose: bool = False) -> int:
    """Load rost (household roster) table."""
    if verbose:
        print("  Loading rost...")
    
    rows_parsed = parse_dat_file(zip_bytes)
    if not rows_parsed:
        return 0
    
    mgr = get_atus_database_manager()
    
    rost_rows = []
    for row in rows_parsed:
        rost_rows.append({
            'TUCASEID': row.get('TUCASEID'),
            'TULINENO': normalize_value(row.get('TULINENO')),
            'TERRP': normalize_value(row.get('TERRP')),
            'TEAGE': normalize_value(row.get('TEAGE')),
            'TESEX': normalize_value(row.get('TESEX')),
        })
    
    success, error = mgr.insert_rost_rows(rost_rows)
    if not success:
        print(f"    [ERROR] {error}")
        return 0
    
    if verbose:
    return len(rost_rows)


def load_rostec(zip_bytes: bytes, verbose: bool = False) -> int:
    """Load rostec (elder care roster) table."""
    if verbose:
        print("  Loading rostec...")
    
    rows_parsed = parse_dat_file(zip_bytes)
    if not rows_parsed:
        return 0
    
    mgr = get_atus_database_manager()
    
    rostec_rows = []
    for row in rows_parsed:
        # TULINENO can be -1, but we normalize that to None, which violates NOT NULL
        # So keep -1 as -1 for this column
        tulineno_raw = row.get('TULINENO', '').strip()
        tulineno = int(tulineno_raw) if tulineno_raw and tulineno_raw != '' else None
        
        if tulineno is None:
            continue  # Skip rows without valid TULINENO
        
        rostec_rows.append({
            'TUCASEID': row.get('TUCASEID'),
            'TUECLNO': normalize_value(row.get('TUECLNO')),
            'TULINENO': tulineno,  # Keep -1 as -1
            'TEAGE_EC': normalize_value(row.get('TEAGE_EC')),
            'TEELDUR': normalize_value(row.get('TEELDUR')),
            'TEELWHO': normalize_value(row.get('TEELWHO')),
            'TEELYRS': normalize_value(row.get('TEELYRS')),
            'TRELHH': normalize_value(row.get('TRELHH')),
        })
    
    success, error = mgr.insert_rostec_rows(rostec_rows)
    if not success:
        print(f"    [ERROR] {error}")
        return 0
    
    if verbose:
    return len(rostec_rows)


def load_atusact(zip_bytes: bytes, verbose: bool = False) -> int:
    """Load atusact (activity) table. Uses batching for large datasets."""
    if verbose:
        print("  Loading atusact...")
    
    rows_parsed = parse_dat_file(zip_bytes)
    if not rows_parsed:
        return 0
    
    mgr = get_atus_database_manager()
    
    atusact_rows = []
    for row in rows_parsed:
        atusact_rows.append({
            'TUCASEID': row.get('TUCASEID'),
            'TUACTIVITY_N': normalize_value(row.get('TUACTIVITY_N')),
            'TUACTDUR24': normalize_value(row.get('TUACTDUR24')),
            'TUCC5': normalize_value(row.get('TUCC5')),
            'TUCC5B': normalize_value(row.get('TUCC5B')),
            'TRTCCTOT_LN': normalize_value(row.get('TRTCCTOT_LN')),
            'TRTCC_LN': normalize_value(row.get('TRTCC_LN')),
            'TRTCOC_LN': normalize_value(row.get('TRTCOC_LN')),
            'TUSTARTTIM': normalize_value(row.get('TUSTARTTIM'), 'str'),
            'TUSTOPTIME': normalize_value(row.get('TUSTOPTIME'), 'str'),
            'TRCODEP': normalize_value(row.get('TRCODEP'), 'str'),
            'TRTIER1P': normalize_value(row.get('TRTIER1P')),
            'TRTIER2P': normalize_value(row.get('TRTIER2P')),
            'TUCC8': normalize_value(row.get('TUCC8')),
            'TUCUMDUR': normalize_value(row.get('TUCUMDUR')),
            'TUCUMDUR24': normalize_value(row.get('TUCUMDUR24')),
            'TUACTDUR': normalize_value(row.get('TUACTDUR')),
            'TR_03CC57': normalize_value(row.get('TR_03CC57')),
            'TRTO_LN': normalize_value(row.get('TRTO_LN')),
            'TRTONHH_LN': normalize_value(row.get('TRTONHH_LN')),
            'TRTOHH_LN': normalize_value(row.get('TRTOHH_LN')),
            'TRTHH_LN': normalize_value(row.get('TRTHH_LN')),
            'TRTNOHH_LN': normalize_value(row.get('TRTNOHH_LN')),
            'TEWHERE': normalize_value(row.get('TEWHERE')),
            'TUCC7': normalize_value(row.get('TUCC7')),
            'TRWBELIG': normalize_value(row.get('TRWBELIG')),
            'TRTEC_LN': normalize_value(row.get('TRTEC_LN')),
            'TUEC24': normalize_value(row.get('TUEC24')),
            'TUDURSTOP': normalize_value(row.get('TUDURSTOP')),
        })
    
    # Single adaptive insert across entire dataset; manager handles batch sizing
    success, error = mgr.insert_atusact_rows(atusact_rows)
    if not success:
        print(f"    [ERROR] atusact insert failed: {error}")
        return 0
    if verbose:
    return len(atusact_rows)


def load_who(zip_bytes: bytes, verbose: bool = False) -> int:
    """Load who ("who was with you") table. Uses batching."""
    if verbose:
        print("  Loading who...")
    
    rows_parsed = parse_dat_file(zip_bytes)
    if not rows_parsed:
        return 0
    
    mgr = get_atus_database_manager()
    
    who_rows = []
    for row in rows_parsed:
        who_rows.append({
            'TUCASEID': row.get('TUCASEID'),
            'TULINENO': normalize_value(row.get('TULINENO')),
            'TUACTIVITY_N': normalize_value(row.get('TUACTIVITY_N')),
            'TRWHONA': normalize_value(row.get('TRWHONA')),
            'TUWHO_CODE': normalize_value(row.get('TUWHO_CODE')),
        })
    
    # Single adaptive insert across entire dataset; manager handles batch sizing
    success, error = mgr.insert_who_rows(who_rows)
    if not success:
        print(f"    [ERROR] who insert failed: {error}")
        return 0
    if verbose:
    return len(who_rows)


def load_cps(zip_bytes: bytes, verbose: bool = False, dat_file: Optional[Path] = None) -> int:
    """
    Load CPS table (265 columns, dynamic) using streaming to avoid high memory usage.
    If dat_file is provided, stream from the local .dat file (test mode).
    Otherwise, stream from the provided ZIP bytes (production mode).
    """
    if verbose:
        print("  Loading cps...")
    
    mgr = get_atus_database_manager()
    
    # Choose input source
    def _row_iter():
        if dat_file is not None:
            # Stream from local file
            with open(dat_file, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield row
        else:
            # Stream from ZIP bytes
            if not zip_bytes:
                return
            try:
                with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
                    dat_members = [zi for zi in zf.infolist() if zi.filename.lower().endswith('.dat')]
                    if not dat_members:
                        return
                    member = dat_members[0]
                    with zf.open(member, 'r') as f:
                        text_stream = TextIOWrapper(f, encoding='utf-8', errors='ignore')
                        reader = csv.DictReader(text_stream)
                        for row in reader:
                            yield row
            except Exception:
                return

    # CPS has 265 columns - use moderate batches and let adaptive batching handle failures
    # Starting with 500 rows: 265 cols × 500 = 132.5k values per INSERT
    # If this fails, adaptive batching will reduce to 250, 125, etc. automatically
    # This reduces DB round trips significantly vs 100-row batches
    batch_size = 5000  # Moderate batch size - adaptive batching will reduce if needed
    total_inserted = 0
    current_batch: List[Dict[str, Any]] = []

    # Pre-compute column type mappings ONCE (not per row) - massive performance improvement
    # Get first row to determine all columns
    row_iter = _row_iter()
    first_row = next(row_iter, None)
    if not first_row:
        return 0
    
    # Build column type mapping
    float_cols = {'HRHHID', 'HRHHID2', 'TUBWGT', 'TUFNWGTP', 'TU20FWGT'}
    str_cols = {'HRSERSUF', 'TRFNLOUT'}
    col_type_map = {}
    for key in first_row.keys():
        if key in float_cols:
            col_type_map[key] = 'float'
        elif key in str_cols or key.endswith('_ID'):
            col_type_map[key] = 'str'
        else:
            col_type_map[key] = 'int'
    
    # Re-create iterator with first row included
    def _row_iter_with_first():
        yield first_row
        for row in row_iter:
            yield row
    
    # Stream-normalize rows and insert in batches
    # Use file=sys.stderr so tqdm doesn't interfere with logger warnings to stdout
    pbar = tqdm(desc="    Loading cps", disable=not verbose, unit="rows", file=sys.stderr, mininterval=0.5)
    try:
        for row in _row_iter_with_first():
            # Use pre-computed type map instead of per-row if/elif checks
            normalized_row = {key: normalize_value(val, col_type_map.get(key, 'int')) 
                             for key, val in row.items()}
            current_batch.append(normalized_row)
    
            if len(current_batch) >= batch_size:
                success, error = mgr.insert_cps_rows(current_batch)
                if not success:
                    pbar.close()
                    print(f"    [ERROR] Batch {(total_inserted // batch_size) + 1}: {error}")
                    return total_inserted
                total_inserted += len(current_batch)
                pbar.update(len(current_batch))
                current_batch = []

        # Flush remaining rows
        if current_batch:
            success, error = mgr.insert_cps_rows(current_batch)
            if not success:
                pbar.close()
                print(f"    [ERROR] Final batch: {error}")
                return total_inserted
            total_inserted += len(current_batch)
            pbar.update(len(current_batch))
    finally:
        pbar.close()
    
    if verbose:
    return total_inserted


def load_resp(zip_bytes: bytes, verbose: bool = False) -> int:
    """Load resp table (133 columns, dynamic). Uses batching."""
    if verbose:
        print("  Loading resp...")
    
    rows_parsed = parse_dat_file(zip_bytes)
    if not rows_parsed:
        return 0
    
    mgr = get_atus_database_manager()
    
    # Normalize all values
    resp_rows = []
    for row in rows_parsed:
        normalized_row = {}
        for key, val in row.items():
            # Weight columns are floats
            if key in ('TUFNWGTP', 'TU20FWGT'):
                normalized_row[key] = normalize_value(val, 'float')
            else:
                normalized_row[key] = normalize_value(val, 'int')
        resp_rows.append(normalized_row)
    
    # Batch insert
    total_inserted = 0
    batch_size = INSERTION_BATCH_SIZE // 15 if INSERTION_BATCH_SIZE > 15 else 1 # Smaller batches due to 133 columns
    pbar = tqdm(total=len(resp_rows), desc="    Loading resp", disable=not verbose, unit="rows")
    try:
        for i in range(0, len(resp_rows), batch_size):
            batch = resp_rows[i:i+batch_size]
            success, error = mgr.insert_resp_rows(batch)
            if not success:
                pbar.close()
                print(f"    [ERROR] Batch {i//batch_size + 1}: {error}")
                return total_inserted
            total_inserted += len(batch)
            pbar.update(len(batch))
    finally:
        pbar.close()
    
    if verbose:
    return total_inserted


def recreate_atus_database(verbose: bool = False) -> bool:
    """Drop and recreate the entire ATUS database from schema file."""
    if verbose:
        print("\n" + "="*80)
        print("RECREATING ATUS DATABASE")
        print("="*80)
    
    from Database.config import get_db_manager
    
    schema_path = Path(__file__).resolve().parents[2] / "Setup" / "Database" / "schemas" / "16_atus.sql"
    
    if not schema_path.exists():
        print(f"[ERROR] Schema file not found: {schema_path}")
        return False
    
    if verbose:
        print(f"  Reading schema from {schema_path.name}...")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # Split into statements
    statements = []
    current_statement = []
    
    for line in schema_sql.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('--'):
            continue
        
        current_statement.append(line)
        
        if stripped.endswith(';'):
            full_statement = '\n'.join(current_statement)
            statements.append(full_statement)
            current_statement = []
    
    if verbose:
        print(f"  Executing {len(statements)} SQL statements...")
    
    db_manager = get_db_manager()
    
    try:
        conn = db_manager.get_connection("mysql")  # Connect to mysql db, not world_sim_atus
        cursor = conn.cursor()
        
        for idx, stmt in enumerate(statements):
            try:
                cursor.execute(stmt)
                conn.commit()
                if verbose and (idx % 5 == 0 or 'DROP DATABASE' in stmt or 'CREATE DATABASE' in stmt):
                    stmt_preview = stmt[:60].replace('\n', ' ') + '...' if len(stmt) > 60 else stmt.replace('\n', ' ')
                    print(f"    [{idx+1}/{len(statements)}] {stmt_preview}")
            except Exception as e:
                # Continue on error for DROP statements
                if not stmt.strip().upper().startswith('DROP'):
                    print(f"    [ERROR] Statement {idx+1}: {e}")
                    return False
        
        cursor.close()
        conn.close()
        
        if verbose:
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to recreate database: {e}")
        return False


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Download and load ATUS data")
    parser.add_argument('--verbose', '-v', action='store_true', help="Verbose output")
    parser.add_argument('--limit-files', nargs='+', help="Only load specific file types (e.g., atussum atusact)")
    parser.add_argument('--test-mode', action='store_true', help="Load from local test files instead of downloading")
    parser.add_argument('--test-data-dir', default='/Users/tristanbrigham/Desktop/Classes/Thesis/Test_Data/ATUS',
                        help="Directory containing test ATUS .dat files")
    parser.add_argument('--no-recreate', action='store_true', help="Skip database recreation (faster for incremental loads)")
    args = parser.parse_args(argv)
    
    print("="*80)
    print("ATUS DATA LOADER")
    if args.test_mode:
        print("(TEST MODE - loading from local files)")
    print("="*80)
    
    # Recreate database unless --no-recreate is specified
    if not args.no_recreate:
        if not recreate_atus_database(verbose=args.verbose):
            print("[ERROR] Failed to recreate database")
            return 1
    else:
        if args.verbose:
            print("\n[INFO] Skipping database recreation (--no-recreate specified)")
    
    discovered_end_suffix: Optional[str] = None
    test_data_path = Path(args.test_data_dir) if args.test_mode else None
    
    if args.test_mode:
        # Test mode: use local files
        print(f"\nUsing test data from: {test_data_path}")
        # Infer end suffix from available files
        dat_files = list(test_data_path.glob("*.dat"))
        if not dat_files:
            print(f"[ERROR] No .dat files found in {test_data_path}")
            return 1
        # Look for a file with year suffix pattern (e.g., atussum_0324.dat)
        for f in dat_files:
            # Extract year suffix from filename like atussum_0324.dat or atuscase_0524.dat
            parts = f.stem.split('_')
            if len(parts) == 2 and len(parts[1]) == 4:
                discovered_end_suffix = parts[1][-2:]  # Last 2 digits
                break
        if not discovered_end_suffix:
            discovered_end_suffix = "24"  # Default to 2024
    else:
        # Production mode: discover and download from API (without materializing huge files in memory)
        session = create_http_session()
        current_year = datetime.now().year
        start_suffix = current_year % 100
        
        print("\nDiscovering latest available ATUS data...")
        probe_filetype = "atusresp"
        
        for end in range(start_suffix, 1, -1):
            end_suffix = f"{end:02d}"
            stem = build_multi_year_stem(probe_filetype, end_suffix)
            url = f"{BASE_URL}/{stem}.zip"
            zip_bytes = fetch_zip_bytes(session, url, verbose=False)
            if not zip_bytes:
                continue
            # Light validation: ensure a .dat member exists
            try:
                with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
                    if any(zi.filename.lower().endswith('.dat') for zi in zf.infolist()):
                        discovered_end_suffix = end_suffix
                        break
            except Exception:
                continue
        
        if not discovered_end_suffix:
            print("[ERROR] No ATUS data available")
            return 1
    
    # Decide whether to (re)load mapping_codes
    # Only needed if recreating DB or if atusact will be loaded
    should_refresh_mapping_codes = not args.no_recreate
    
    # File type to loader function mapping
    loaders = {
        'atussum': [load_case_id_from_atussum, load_sum_from_atussum],
        'atuswgts': [load_weights],
        'atuscase': [load_atuscase],
        'atusrost': [load_rost],
        'atusrostec': [load_rostec],
        'atusact': [load_atusact],
        'atuswho': [load_who],
        'atuscps': [load_cps],
        'atusresp': [load_resp],
    }
    
    # Filter if --limit-files specified
    if args.limit_files:
        loaders = {k: v for k, v in loaders.items() if k in args.limit_files}
    # Recompute mapping refresh need based on selected loaders
    if args.no_recreate and 'atusact' not in loaders:
        should_refresh_mapping_codes = False

    # Conditionally refresh mapping_codes
    if should_refresh_mapping_codes:
        print("\nLoading activity code mappings (mapping_codes table)...")
        print("  Running process_atus.py to populate mapping_codes...")
        import subprocess
        process_atus_path = Path(__file__).parent / "process_atus.py"
        result = subprocess.run(
            ["python3", str(process_atus_path)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"[ERROR] Failed to load mapping_codes: {result.stderr}")
            return 1
    
    print(f"\nLoading {len(loaders)} file types...")
    
    # Use a temporary directory for downloaded files in production mode; cleaned after run
    with (tempfile.TemporaryDirectory() if not args.test_mode else nullcontext()) as _tmpdir:
        tmpdir = Path(_tmpdir) if _tmpdir else None
    
    for filetype in loaders.keys():
        print(f"\n{filetype}:")
        
        if args.test_mode:
            # Test mode: read from local .dat file
            # Try different naming patterns (e.g., atussum_0324.dat, atuscase_0524.dat)
            dat_file = None
            for pattern in [f"{filetype}_*.dat", f"{filetype}-*.dat"]:
                matches = list(test_data_path.glob(pattern))
                if matches:
                    dat_file = matches[0]
                    break
            
            if not dat_file or not dat_file.exists():
                print(f"  [WARN] No .dat file found for {filetype}")
                continue
            
            print(f"  Loading from {dat_file.name}...")
            if filetype == 'atuscps':
                # Stream CPS directly from file (do not read entire file)
                for loader_func in loaders[filetype]:
                    count = loader_func(None, verbose=args.verbose, dat_file=dat_file)
            else:
                # Read .dat file directly (no ZIP in test mode) for non-streaming loaders
                with open(dat_file, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    rows_parsed = list(reader)
            
            # Create a mock parse function that returns the rows
            def mock_parse(dummy):
                return rows_parsed
            
                    # Call loaders using mocked parse
            for loader_func in loaders[filetype]:
                original_parse = globals()['parse_dat_file']
                globals()['parse_dat_file'] = mock_parse
                try:
                    count = loader_func(None, verbose=args.verbose)
                finally:
                    globals()['parse_dat_file'] = original_parse
        else:
                # Production mode: download ZIP to temp dir and extract .dat
            stem = build_multi_year_stem(filetype, discovered_end_suffix)
            url = f"{BASE_URL}/{stem}.zip"
            
            zip_bytes = fetch_zip_bytes(session, url, verbose=args.verbose)
            if not zip_bytes:
                print(f"  [WARN] Failed to download {url}")
                continue
            
                if not tmpdir:
                    print("  [ERROR] Temporary directory not available")
                    return 1

                zip_path = tmpdir / f"{stem}.zip"
                with open(zip_path, 'wb') as zf:
                    zf.write(zip_bytes)

                # Extract .dat to disk
                dat_file = None
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        dat_members = [zi for zi in zf.infolist() if zi.filename.lower().endswith('.dat')]
                        if not dat_members:
                            print(f"  [WARN] ZIP had no .dat for {filetype}")
                            continue
                        member = dat_members[0]
                        dat_file = tmpdir / Path(member.filename).name
                        with zf.open(member, 'r') as src, open(dat_file, 'wb') as dst:
                            dst.write(src.read())
                except Exception as e:
                    print(f"  [WARN] Could not extract .dat for {filetype}: {e}")
                continue
            
                # Dispatch to loaders from local .dat
                if filetype == 'atuscps':
                    for loader_func in loaders[filetype]:
                        count = loader_func(None, verbose=args.verbose, dat_file=dat_file)
                else:
                    # For non-streaming loaders, read rows to memory (smaller datasets)
                    with open(dat_file, 'r', encoding='utf-8', errors='ignore') as f:
                        reader = csv.DictReader(f)
                        rows_parsed = list(reader)

                    def mock_parse(dummy):
                        return rows_parsed

            for loader_func in loaders[filetype]:
                        original_parse = globals()['parse_dat_file']
                        globals()['parse_dat_file'] = mock_parse
                        try:
                            count = loader_func(None, verbose=args.verbose)
                        finally:
                            globals()['parse_dat_file'] = original_parse
    
    print("\n" + "="*80)
    print("="*80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


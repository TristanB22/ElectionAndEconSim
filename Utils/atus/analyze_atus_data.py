#!/usr/bin/env python3
"""
Analyze ATUS .dat files to understand structure, determine appropriate primary keys,
and validate relationships for proper schema design.
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import Counter
import csv

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Test data directory
TEST_DATA_DIR = Path("/Users/tristanbrigham/Desktop/Classes/Thesis/Test_Data/ATUS")

# Files we're analyzing (matching the loader)
FILES_TO_ANALYZE = {
    "atusact": "atusact_0324.dat",
    "atuscase": "atuscase_0524.dat",
    "atuscps": "atuscps_0324.dat",
    "atusresp": "atusresp_0324.dat",
    "atusrost": "atusrost_0324.dat",
    "atusrostec": "atusrostec_1124.dat",
    "atussum": "atussum_0324.dat",
    "atuswgts": "atuswgts_0324.dat",
    "atuswho": "atuswho_0324.dat",
}


def analyze_file_structure(file_path: Path, max_rows: int = 10000) -> Dict:
    """Analyze a .dat file to understand its structure and key patterns."""
    print(f"\n{'='*80}")
    print(f"Analyzing: {file_path.name}")
    print(f"{'='*80}")
    
    if not file_path.exists():
        print(f"  [SKIP] File not found")
        return {}
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        headers = next(reader)
        num_cols = len(headers)
        
        print(f"  Columns: {num_cols}")
        print(f"  First 5 columns: {headers[:5]}")
        if num_cols > 5:
            print(f"  Last 5 columns: {headers[-5:]}")
        
        # Track column value patterns
        rows_processed = 0
        column_values: Dict[str, Set] = {h: set() for h in headers}
        column_nulls: Dict[str, int] = {h: 0 for h in headers}
        
        for row in reader:
            if rows_processed >= max_rows:
                break
            
            # Pad row if needed
            while len(row) < num_cols:
                row.append("")
            
            for idx, val in enumerate(row[:num_cols]):
                col_name = headers[idx]
                val_stripped = val.strip()
                
                # Track unique values (limit to avoid memory issues)
                if len(column_values[col_name]) < 1000:
                    column_values[col_name].add(val_stripped)
                
                # Track nulls/missing (-1 is common null indicator in ATUS)
                if val_stripped in ("", "-1"):
                    column_nulls[col_name] += 1
            
            rows_processed += 1
        
        print(f"  Rows analyzed: {rows_processed}")
        
        # Identify potential key columns
        print(f"\n  Potential Key Analysis:")
        
        # Check TUCASEID uniqueness
        if "TUCASEID" in column_values:
            tucaseid_count = len(column_values["TUCASEID"])
            print(f"    TUCASEID: {tucaseid_count} unique values (rows: {rows_processed})")
            if tucaseid_count == rows_processed:
                print(f"      -> TUCASEID is UNIQUE (potential PK)")
            else:
                print(f"      -> TUCASEID has duplicates")
        
        # Check common composite key candidates
        composite_candidates = [
            ("TUCASEID", "TULINENO"),
            ("TUCASEID", "TUACTIVITY_N"),
            ("TUCASEID", "TUECLNO"),
            ("TUCASEID", "weight_number"),
        ]
        
        for combo in composite_candidates:
            if all(c in headers for c in combo):
                # Count unique combinations
                combo_set = set()
                f.seek(0)
                reader = csv.reader(f)
                next(reader)  # skip header
                count = 0
                for row in reader:
                    if count >= max_rows:
                        break
                    while len(row) < num_cols:
                        row.append("")
                    combo_vals = tuple(row[headers.index(c)] for c in combo)
                    combo_set.add(combo_vals)
                    count += 1
                
                combo_count = len(combo_set)
                print(f"    {' + '.join(combo)}: {combo_count} unique (rows: {count})")
                if combo_count == count:
                    print(f"      -> Composite key is UNIQUE (potential PK)")
        
        # Report columns with high null rates
        print(f"\n  Columns with >50% nulls/missing:")
        high_null_cols = [(col, cnt / rows_processed) for col, cnt in column_nulls.items() 
                          if rows_processed > 0 and (cnt / rows_processed) > 0.5]
        high_null_cols.sort(key=lambda x: x[1], reverse=True)
        for col, null_rate in high_null_cols[:10]:
            print(f"    {col}: {column_nulls[col]}/{rows_processed} ({null_rate*100:.1f}%)")
        
        return {
            "file": file_path.name,
            "columns": headers,
            "num_cols": num_cols,
            "rows_analyzed": rows_processed,
            "column_values": column_values,
            "column_nulls": column_nulls,
        }


def main():
    print("ATUS Data Structure Analysis")
    print("=" * 80)
    
    results = {}
    for file_type, filename in FILES_TO_ANALYZE.items():
        file_path = TEST_DATA_DIR / filename
        result = analyze_file_structure(file_path, max_rows=50000)
        results[file_type] = result
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print("\nFiles analyzed:")
    for file_type, result in results.items():
        if result:
            print(f"  {file_type}: {result['num_cols']} columns, {result['rows_analyzed']} rows")
    
    print("\nRecommendations:")
    print("  1. case_id table: TUCASEID should be PK")
    print("  2. resp/cps/rost: (TUCASEID, TULINENO) composite PK")
    print("  3. who/atusact: (TUCASEID, TUACTIVITY_N, ...) composite PK")
    print("  4. weights: normalize to (TUCASEID, weight_number)")
    print("  5. sum: normalize to (TUCASEID, activity_code)")


if __name__ == "__main__":
    main()


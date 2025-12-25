#!/usr/bin/env python3
"""
Deep analysis of ATUS files to understand proper primary keys
"""

import sys
from pathlib import Path
import csv
from collections import defaultdict

TEST_DATA_DIR = Path("/Users/tristanbrigham/Desktop/Classes/Thesis/Test_Data/ATUS")

def analyze_who_keys():
    """atuswho has TUCASEID, TULINENO, TUACTIVITY_N, TRWHONA, TUWHO_CODE
    Need to determine proper PK"""
    print("\n" + "="*80)
    print("ATUSWHO KEY ANALYSIS")
    print("="*80)
    
    file_path = TEST_DATA_DIR / "atuswho_0324.dat"
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        headers = next(reader)
        print(f"Columns: {headers}")
        
        # Test various key combinations
        keys_2col = set()  # (TUCASEID, TULINENO)
        keys_3col_a = set()  # (TUCASEID, TUACTIVITY_N, TUWHO_CODE)
        keys_3col_b = set()  # (TUCASEID, TULINENO, TUACTIVITY_N)
        keys_4col = set()  # (TUCASEID, TULINENO, TUACTIVITY_N, TUWHO_CODE)
        
        count = 0
        for row in reader:
            if count >= 100000:
                break
            keys_2col.add((row[0], row[1]))  # TUCASEID, TULINENO
            keys_3col_a.add((row[0], row[2], row[4]))  # TUCASEID, TUACTIVITY_N, TUWHO_CODE
            keys_3col_b.add((row[0], row[1], row[2]))  # TUCASEID, TULINENO, TUACTIVITY_N
            keys_4col.add((row[0], row[1], row[2], row[4]))  # All except TRWHONA
            count += 1
        
        print(f"Rows: {count}")
        print(f"(TUCASEID, TULINENO): {len(keys_2col)} unique")
        print(f"(TUCASEID, TUACTIVITY_N, TUWHO_CODE): {len(keys_3col_a)} unique")
        print(f"(TUCASEID, TULINENO, TUACTIVITY_N): {len(keys_3col_b)} unique")
        print(f"(TUCASEID, TULINENO, TUACTIVITY_N, TUWHO_CODE): {len(keys_4col)} unique")
        
        if len(keys_4col) == count:
        elif len(keys_3col_a) == count:
        else:
            print("✗ Need 5-column key including TRWHONA")


def analyze_atuscase_keys():
    """atuscase has TUCASEID as first column - but analysis showed duplicates
    Need to understand why"""
    print("\n" + "="*80)
    print("ATUSCASE KEY ANALYSIS")
    print("="*80)
    
    file_path = TEST_DATA_DIR / "atuscase_0524.dat"
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        headers = next(reader)
        print(f"Columns: {headers}")
        
        tucaseid_counts = defaultdict(int)
        count = 0
        first_duplicate = None
        
        for row in reader:
            if count >= 100000:
                break
            tucaseid = row[0]
            tucaseid_counts[tucaseid] += 1
            if tucaseid_counts[tucaseid] == 2 and first_duplicate is None:
                first_duplicate = tucaseid
            count += 1
        
        print(f"Rows: {count}")
        print(f"Unique TUCASEID: {len(tucaseid_counts)}")
        
        duplicates = {k: v for k, v in tucaseid_counts.items() if v > 1}
        print(f"Duplicates: {len(duplicates)}")
        
        if duplicates:
            print(f"\nFirst duplicate TUCASEID: {first_duplicate} (appears {tucaseid_counts[first_duplicate]} times)")
            print("Sample duplicates:")
            for k, v in list(duplicates.items())[:5]:
                print(f"  {k}: {v} times")
        else:


def analyze_atussum_structure():
    """atussum has ~456 columns starting with TUCASEID, then demographic fields,
    then t010101, t010102, ... t509989 (activity time columns).
    Should be normalized to (TUCASEID, activity_code, minutes)"""
    print("\n" + "="*80)
    print("ATUSSUM STRUCTURE ANALYSIS")
    print("="*80)
    
    file_path = TEST_DATA_DIR / "atussum_0324.dat"
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        headers = next(reader)
        
        # Find where activity columns start (columns starting with 't')
        activity_cols = [h for h in headers if h.startswith('t') and h[1:].isdigit()]
        demographic_cols = [h for h in headers if not (h.startswith('t') and h[1:].isdigit())]
        
        print(f"Total columns: {len(headers)}")
        print(f"Demographic columns: {len(demographic_cols)}")
        print(f"Activity time columns: {len(activity_cols)}")
        print(f"\nFirst 10 activity columns: {activity_cols[:10]}")
        print(f"Last 10 activity columns: {activity_cols[-10:]}")
        print(f"\nDemographic columns: {demographic_cols}")
        
        # Check TUCASEID uniqueness
        tucaseid_set = set()
        count = 0
        for row in reader:
            if count >= 50000:
                break
            tucaseid_set.add(row[0])
            count += 1
        
        print(f"\nRows: {count}")
        print(f"Unique TUCASEID: {len(tucaseid_set)}")
        if len(tucaseid_set) == count:
            print("→ Normalize to: case_id table (demographics) + sum table (TUCASEID, activity_code, minutes)")


def analyze_weights_structure():
    """atuswgts has TUCASEID + TUFNWGTP001..TUFNWGTP160
    Should be normalized to (TUCASEID, weight_number, weight_value)"""
    print("\n" + "="*80)
    print("WEIGHTS STRUCTURE ANALYSIS")
    print("="*80)
    
    file_path = TEST_DATA_DIR / "atuswgts_0324.dat"
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        headers = next(reader)
        
        print(f"Total columns: {len(headers)}")
        print(f"First 5 columns: {headers[:5]}")
        print(f"Last 5 columns: {headers[-5:]}")
        
        # Verify pattern
        weight_cols = [h for h in headers if h.startswith('TUFNWGTP') and h != 'TUFNWGTP']
        print(f"\nWeight columns: {len(weight_cols)}")
        print(f"Expected: TUFNWGTP001..TUFNWGTP160 (160 columns)")
        
        # Check TUCASEID uniqueness
        tucaseid_set = set()
        count = 0
        for row in reader:
            if count >= 50000:
                break
            tucaseid_set.add(row[0])
            count += 1
        
        print(f"\nRows: {count}")
        print(f"Unique TUCASEID: {len(tucaseid_set)}")
        if len(tucaseid_set) == count:
            print("→ Normalize to: (TUCASEID, weight_number, weight_value)")


def main():
    print("DETAILED KEY ANALYSIS FOR ATUS FILES")
    analyze_atuscase_keys()
    analyze_who_keys()
    analyze_atussum_structure()
    analyze_weights_structure()


if __name__ == "__main__":
    main()


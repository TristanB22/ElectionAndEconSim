import os
import sys
from pathlib import Path
from typing import List, Tuple

# Ensure project root is on sys.path for absolute imports like 'Database.config'
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from Database.config import get_db_manager

input_path = "/Users/tristanbrigham/Desktop/Classes/Thesis/World_Sim/Data/ATUS/atus_lexicon_first_screenshot.tsv"

def split_row(row):
    # Split TSV, pad with empty to at least 6 cols
    cols = row.rstrip("\n\r").split("\t")
    while len(cols) < 6:
        cols.append("")
    return cols

# At the end of processing, append these lines ONCE (not inside the input loop)
temp_tsv_lines = [
    "18\tTraveling\t1813\tTravel Related to Sports, Exercise, and Recreation\t181301\tTravel related to participating in sports/exercise/recreation\tincludes 171301 (2003–2004); 181301 (2005 and later years)\n",
    "18\tTraveling\t1813\tTravel Related to Sports, Exercise, and Recreation\t181302\tTravel related to attending sporting/recreational events\tincludes 171302 (2003–2004); 181302 (2005 and later years)\n",
    "18\tTraveling\t1813\tTravel Related to Sports, Exercise, and Recreation\t181399\tTravel related to sports, exercise, & recreation, n.e.c.*\tincludes 171399 (2003–2004); 181399 (2005 and later years)\n",
    "18\tTraveling\t1814\tTravel Related to Religious/Spiritual Activities\t181401\tTravel related to religious/spiritual practices\tincludes 171401 (2003–2004); 181401 (2005 and later years)\n",
    "18\tTraveling\t1814\tTravel Related to Religious/Spiritual Activities\t181499\tTravel rel. to religious/spiritual activities, n.e.c.*\tincludes 171499 (2003–2004); 181499 (2005 and later years)\n",
    "18\tTraveling\t1815\tTravel Related to Volunteer Activities\t181501\tTravel related to volunteering\tincludes 171501 (2003–2004); 181501 (2005 and later years)\n",
    "18\tTraveling\t1815\tTravel Related to Volunteer Activities\t181599\tTravel related to volunteer activities, n.e.c.*\tincludes 171599 (2003–2004); 181599 (2005 and later years)\n",
    "18\tTraveling\t1816\tTravel Related to Telephone Calls\t181601\tTravel related to phone calls\tincludes 171601 (2003–2004); 181601 (2005 and later years)\n",
    "18\tTraveling\t1816\tTravel Related to Telephone Calls\t181699\tTravel rel. to phone calls, n.e.c.*\tincludes 171699 (2003–2004); 181699 (2005 and later years)\n",
    "18\tTraveling\t1818\tSecurity Procedures Related to Traveling\t181801\tSecurity procedures related to traveling\tincludes 171701 (2003–2004); 181801 (2005 and later years)\n",
    "18\tTraveling\t1818\tSecurity Procedures Related to Traveling\t181899\tSecurity procedures related to traveling, n.e.c.*\tincludes 171799 (2003–2004); 181899 (2005 and later years)\n",
    "18\tTraveling\t1899\tTraveling, n.e.c.*\t189999\tTraveling, n.e.c.*\tincludes 179999 (2003–2004); 189999 (2005 and later years)\n",
    "50\tData Codes\t5001\tUnable to Code\t500101\tInsufficient detail in verbatim\t\n",
    "50\tData Codes\t5001\tUnable to Code\t500103\tMissing travel or destination\t\n",
    "50\tData Codes\t5001\tUnable to Code\t500104\tRecorded simultaneous activities incorrectly\tcode was used in 2003–2012 only\n",
    "50\tData Codes\t5001\tUnable to Code\t500105\tRespondent refused to provide information/\"none of your business\"\t\n",
    "50\tData Codes\t5001\tUnable to Code\t500106\tGap/can’t remember\t\n",
    "50\tData Codes\t5001\tUnable to Code\t500107\tUnable to code activity at 1st tier\t\n",
    "50\tData Codes\t5099\tData codes, n.e.c.*\t509989\tData codes, n.e.c.*\tincludes 500102 (2003); 509999 (All years)\n"
]

def _get_db_connection():
    # Use centralized DB manager (NAS or Docker decided by config/.env)
    dbm = get_db_manager()
    return dbm.get_connection("world_sim_atus")


def _truncate_mapping_codes(cur) -> None:
    # Can't use TRUNCATE due to foreign key constraints, so DELETE instead
    cur.execute("DELETE FROM world_sim_atus.mapping_codes")


def _insert_mapping_codes(cur, rows: List[Tuple[str, str, str, str, str, str, str]]) -> None:
    sql = (
        "INSERT INTO world_sim_atus.mapping_codes "
        "(major_code, major_name, tier_code, tier_name, six_digit_activity_code, activity, notes) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)"
    )
    cur.executemany(sql, rows)


def main() -> None:
    # Build TSV lines entirely in memory
    output_lines: List[str] = []
    with open(input_path, "r", encoding="utf-8") as fin:
        header_written = False
        major_code, major_name = "", ""
        tier_code, tier_name = "", ""
        for line in fin:
            row = split_row(line)

            if not header_written:
                output_lines.append("major_code\tmajor_name\ttier_code\ttier_name\tsix_digit_activity_code\tactivity\tnotes\n")
                header_written = True
                continue

            if all(x.strip() == "" for x in row[:6]):
                continue

            code = row[0].strip()
            name = row[1].strip()
            if code and len(code) == 2:
                major_code = code
                major_name = name
                tier_code = ""
                tier_name = ""
                continue
            elif code and len(code) == 4:
                tier_code = code
                tier_name = name
                continue
            elif code and len(code) == 6:
                six_code = code
                activity = row[1].strip()
                notes = row[2].strip() if len(row) > 2 else ""
                outline = [
                    major_code,
                    major_name,
                    tier_code,
                    tier_name,
                    six_code,
                    activity,
                ]
                if len(row) > 3:
                    outline.extend(row[2:])
                else:
                    outline.append(notes)
                output_lines.append("\t".join(outline) + "\n")
            # ignore other rows

    # Append the fixed extra lines once
    output_lines.extend(temp_tsv_lines)

    # Convert TSV lines to DB rows (split by tabs after making the file)
    rows: List[Tuple[str, str, str, str, str, str, str]] = []
    for i, line in enumerate(output_lines):
        # Skip header
        if i == 0:
            continue
        cols = line.rstrip("\n\r").split("\t")
        if not cols or all(c.strip() == "" for c in cols):
            continue
        # Ensure at least 7 columns, then merge extra columns into notes
        while len(cols) < 7:
            cols.append("")
        major_code = cols[0].strip()
        major_name = cols[1].strip()
        tier_code = cols[2].strip()
        tier_name = cols[3].strip()
        six_code = cols[4].strip()
        activity = cols[5].strip()
        notes = "\t".join(cols[6:]).strip() if len(cols) > 6 else ""
        if six_code:
            rows.append((major_code, major_name, tier_code, tier_name, six_code, activity, notes))

    if not rows:
        return

    # Save to DB via a simple manager; no files/artifacts written
    conn = _get_db_connection()
    try:
        cur = conn.cursor()
        _truncate_mapping_codes(cur)
        _insert_mapping_codes(cur, rows)
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Backup mapping_codes data, recreate schema, restore mapping_codes
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Database.config import get_db_manager

def main():
    db_manager = get_db_manager()
    conn = None
    cursor = None
    
    try:
        conn = db_manager.get_connection("world_sim_atus")
        cursor = conn.cursor(dictionary=True)
        
        # Step 1: Check and backup mapping_codes
        print("Step 1: Backing up mapping_codes data...")
        cursor.execute("SELECT COUNT(*) as cnt FROM world_sim_atus.mapping_codes")
        result = cursor.fetchone()
        row_count = result['cnt'] if result else 0
        print(f"  Found {row_count} rows in mapping_codes")
        
        backup_data = []
        if row_count > 0:
            cursor.execute("""
                SELECT major_code, major_name, tier_code, tier_name,
                       six_digit_activity_code, activity, notes
                FROM world_sim_atus.mapping_codes
                ORDER BY six_digit_activity_code
            """)
            backup_data = cursor.fetchall()
            print(f"  Backed up {len(backup_data)} rows")
        
        # Step 2: Read and execute new schema
        print("\nStep 2: Executing new schema...")
        schema_path = Path(__file__).resolve().parents[2] / "Setup" / "Database" / "schemas" / "16_atus.sql"
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Split and execute statements
        statements = []
        current_statement = []
        
        for line in schema_sql.split('\n'):
            # Skip comments and empty lines
            stripped = line.strip()
            if not stripped or stripped.startswith('--'):
                continue
            
            current_statement.append(line)
            
            # Check if statement is complete
            if stripped.endswith(';'):
                full_statement = '\n'.join(current_statement)
                statements.append(full_statement)
                current_statement = []
        
        print(f"  Found {len(statements)} SQL statements")
        
        for idx, stmt in enumerate(statements, 1):
            stmt_preview = stmt[:60].replace('\n', ' ') + '...' if len(stmt) > 60 else stmt
            try:
                cursor.execute(stmt)
                conn.commit()
            except Exception as e:
                print(f"    [{idx}/{len(statements)}] ✗ {stmt_preview}")
                print(f"      Error: {e}")
                # Continue on error for DROP statements
                if not stmt.strip().upper().startswith('DROP'):
                    raise
        
        # Step 3: Restore mapping_codes
        if backup_data:
            print(f"\nStep 3: Restoring {len(backup_data)} rows to mapping_codes...")
            insert_sql = """
                INSERT INTO world_sim_atus.mapping_codes
                (major_code, major_name, tier_code, tier_name, six_digit_activity_code, activity, notes)
                VALUES (%(major_code)s, %(major_name)s, %(tier_code)s, %(tier_name)s,
                        %(six_digit_activity_code)s, %(activity)s, %(notes)s)
            """
            cursor.executemany(insert_sql, backup_data)
            conn.commit()
        
        # Step 4: Verify schema
        print("\nStep 4: Verifying schema...")
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'world_sim_atus'
            ORDER BY TABLE_NAME
        """)
        tables = [row['TABLE_NAME'] for row in cursor.fetchall()]
        print(f"  Tables in world_sim_atus:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as cnt FROM world_sim_atus.{table}")
            count = cursor.fetchone()['cnt']
            print(f"    {table}: {count} rows")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        return 1
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())


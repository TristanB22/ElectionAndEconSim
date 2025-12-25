#!/usr/bin/env python3
"""
SQL Execution Utility
Executes SQL files in dependency order for database setup.
"""
import sys
import os
from pathlib import Path
import mysql.connector
from mysql.connector import Error
import json

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Utils.environment_config import get_database_config

def get_database_connection():
    """Get database connection using environment configuration."""
    try:
        db_config = get_database_config()
        
        connection = mysql.connector.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        
        if connection.is_connected():
            print(f"[SUCCESS] Connected to {db_config['target'].upper()} database: {db_config['host']}:{db_config['port']}")
            return connection
    except Error as e:
        print(f"[ERROR] Database connection failed: {e}")
        raise

def execute_sql_file(connection, sql_file_path, database=None):
    """Execute SQL file with proper database context."""
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        # Use subprocess to pipe SQL directly to mysql client for complex files
        import subprocess
        import tempfile
        import os
        
        # Create a temporary file with the SQL content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
            temp_file.write(sql_content)
            temp_file_path = temp_file.name
        
        try:
            # Get database config for connection parameters
            db_config = get_database_config()
            
            # Build mysql command
            mysql_cmd = [
                'mysql',
                '-h', db_config['host'],
                '-P', str(db_config['port']),
                '-u', db_config['user'],
                f'-p{db_config["password"]}'
            ]
            
            # Execute the SQL file
            result = subprocess.run(
                mysql_cmd,
                stdin=open(temp_file_path, 'r'),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"  [SUCCESS] SQL file executed successfully")
                return True
            else:
                print(f"  [ERROR] MySQL execution failed: {result.stderr}")
                return False
                
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
        
    except Exception as e:
        print(f"[ERROR] Error executing {sql_file_path}: {e}")
        return False

def execute_sql_files_in_order(connection, schema_dir, test_data=False, include_geo=False, only_geo=False):
    """Execute SQL files in dependency order."""
    schema_dir = Path(schema_dir)
    
    # Define execution order for core simulation databases
    sql_files = [
        "01_databases.sql",
        "02_agents.sql", 
        "03_firms.sql",
        "04_simulations.sql",
        "05_l2_agent_core.sql",
        "06_l2_location.sql",
        "07_l2_geo.sql",
        "08_l2_political_part_1.sql",
        "08_l2_political_part_2.sql", 
        "08_l2_political_part_3.sql",
        "09_l2_other_part_1.sql",
        "09_l2_other_part_2.sql",
        "09_l2_other_part_3.sql",
        "09_l2_other_part_4.sql",
        "11_conversations_channels.sql",
    ]
    
    # Add geo database if requested
    if include_geo:
        sql_files.append("10_geo_pois.sql")
    
    # If only geo is requested, filter the list
    if only_geo:
        sql_files = ["10_geo_pois.sql"]
    
    print(f"Executing SQL files from {schema_dir}")
    print("=" * 50)
    
    success_count = 0
    total_count = 0
    
    for sql_file in sql_files:
        sql_path = schema_dir / sql_file
        if sql_path.exists():
            print(f"\nExecuting {sql_file}...")
            if execute_sql_file(connection, sql_path):
                success_count += 1
                print(f"  [SUCCESS] {sql_file} completed successfully")
            else:
                print(f"  [FAILED] {sql_file} failed")
            total_count += 1
        else:
            print(f"[WARNING] {sql_file} not found, skipping...")
    
    print("\n" + "=" * 50)
    print(f"SQL Execution Summary: {success_count}/{total_count} files executed successfully")
    
    return success_count == total_count

def load_l2_column_mapping(schema_dir):
    """Load L2 column mapping for data insertion."""
    mapping_file = Path(schema_dir) / "l2_column_mapping.json"
    if mapping_file.exists():
        with open(mapping_file, 'r') as f:
            return json.load(f)
    return None

def insert_l2_test_data(connection, schema_dir):
    """Insert L2 test data using the column mapping."""
    try:
        # Load column mapping
        mapping = load_l2_column_mapping(schema_dir)
        if not mapping:
            print("[ERROR] L2 column mapping not found")
            return False
        
        # Load test data
        csv_path = Path(__file__).resolve().parents[3] / 'Test_Data' / 'L2Data' / 'test_l2_data.csv'
        if not csv_path.exists():
            print(f"[ERROR] L2 test data not found: {csv_path}")
            return False
        
        import pandas as pd
        df = pd.read_csv(csv_path, sep='\t', encoding='latin-1', low_memory=False)
        
        if df.empty:
            print("[WARNING] L2 test data is empty")
            return False
        
        print(f"Loading {len(df)} rows of L2 test data...")
        
        cursor = connection.cursor()
        
        # Switch to agents database for L2 tables
        cursor.execute("USE world_sim_agents")
        
        # Insert into each table
        buckets = mapping['buckets']
        col_map = mapping['safe_column_mapping']
        lat_col = mapping['lat_column']
        lon_col = mapping['lon_column']
        
        # Agent core
        if 'agent_core' in buckets and buckets['agent_core']:
            agent_cols = buckets['agent_core']
            for _, row in df.iterrows():
                lvid = str(row.get('LALVOTERID') or '')
                if not lvid:
                    continue
                
                values = [lvid]
                for col in agent_cols:
                    val = row.get(col)
                    values.append(None if pd.isna(val) else str(val))
                
                placeholders = ', '.join(['%s'] * len(values))
                columns = ['LALVOTERID'] + [f"`{col_map[col]}`" for col in agent_cols]
                
                sql = f"REPLACE INTO l2_agent_core ({', '.join(columns)}) VALUES ({placeholders})"
                cursor.execute(sql, values)
        
        # Location
        if 'location' in buckets and buckets['location']:
            location_cols = buckets['location']
            for _, row in df.iterrows():
                lvid = str(row.get('LALVOTERID') or '')
                if not lvid:
                    continue
                
                values = [lvid]
                for col in location_cols:
                    val = row.get(col)
                    values.append(None if pd.isna(val) else str(val))
                
                placeholders = ', '.join(['%s'] * len(values))
                columns = ['LALVOTERID'] + [f"`{col_map[col]}`" for col in location_cols]
                
                sql = f"REPLACE INTO l2_location ({', '.join(columns)}) VALUES ({placeholders})"
                cursor.execute(sql, values)
        
        # Political tables
        if 'political' in buckets and buckets['political']:
            political_cols = buckets['political']
            # Split into chunks of 120 columns
            chunks = [political_cols[i:i + 120] for i in range(0, len(political_cols), 120)]
            
            for chunk_idx, chunk in enumerate(chunks, 1):
                table_name = f"l2_political_part_{chunk_idx}"
                
                for _, row in df.iterrows():
                    lvid = str(row.get('LALVOTERID') or '')
                    if not lvid:
                        continue
                    
                    values = [lvid]
                    for col in chunk:
                        val = row.get(col)
                        values.append(None if pd.isna(val) else str(val))
                    
                    placeholders = ', '.join(['%s'] * len(values))
                    columns = ['LALVOTERID'] + [f"`{col_map[col]}`" for col in chunk]
                    
                    sql = f"REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                    cursor.execute(sql, values)
        
        # Other tables
        if 'other' in buckets and buckets['other']:
            other_cols = buckets['other']
            # Split into chunks of 120 columns
            chunks = [other_cols[i:i + 120] for i in range(0, len(other_cols), 120)]
            
            for chunk_idx, chunk in enumerate(chunks, 1):
                table_name = f"l2_other_part_{chunk_idx}"
                
                for _, row in df.iterrows():
                    lvid = str(row.get('LALVOTERID') or '')
                    if not lvid:
                        continue
                    
                    values = [lvid]
                    for col in chunk:
                        val = row.get(col)
                        values.append(None if pd.isna(val) else str(val))
                    
                    placeholders = ', '.join(['%s'] * len(values))
                    columns = ['LALVOTERID'] + [f"`{col_map[col]}`" for col in chunk]
                    
                    sql = f"REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                    cursor.execute(sql, values)
        
        # Geo table
        if lat_col and lon_col:
            for _, row in df.iterrows():
                lvid = str(row.get('LALVOTERID') or '')
                if not lvid:
                    continue
                
                lat_raw = row.get(lat_col)
                lon_raw = row.get(lon_col)
                
                try:
                    if pd.notna(lat_raw) and pd.notna(lon_raw):
                        lat = float(str(lat_raw))
                        lon = float(str(lon_raw))
                        cursor.execute(
                            "REPLACE INTO l2_geo (LALVOTERID, latitude, longitude) VALUES (%s, %s, %s)",
                            (lvid, lat, lon)
                        )
                except Exception:
                    pass
        
        connection.commit()
        cursor.close()
        
        print(f"[SUCCESS] L2 test data loaded successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error loading L2 test data: {e}")
        return False

def main():
    """Main function for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Execute SQL files for database setup")
    parser.add_argument("--target", choices=['docker', 'nas'], default='docker', help="Database target")
    parser.add_argument("--test-data", action="store_true", help="Load test data")
    args = parser.parse_args()
    
    # Set environment variable
    os.environ['DATABASE_TARGET'] = args.target
    
    try:
        connection = get_database_connection()
        
        schema_dir = Path(__file__).parent / "schemas"
        
        # Execute SQL files
        success = execute_sql_files_in_order(connection, schema_dir, args.test_data)
        
        if success and args.test_data:
            # Load L2 test data
            insert_l2_test_data(connection, schema_dir)
        
        if success:
            print("\n[SUCCESS] Database setup completed successfully!")
        else:
            print("\n[ERROR] Database setup failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"[ERROR] Setup failed: {e}")
        sys.exit(1)
    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()

if __name__ == '__main__':
    main()

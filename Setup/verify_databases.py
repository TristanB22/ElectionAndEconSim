#!/usr/bin/env python3
"""
Verify Database Tables Script
Verifies that all required tables exist in both NAS and Docker environments.
"""
import sys
import os
import argparse
from pathlib import Path

from Utils.path_manager import initialize_paths
initialize_paths()

from Database.connection_manager import get_db_manager
from Database.database_manager import DatabaseConfig
from Utils.environment_config import get_database_config


def verify_database_tables(target):
    """Verify that all required tables exist for the specified target."""
    print(f"Verifying database tables on {target.upper()}...")
    
    # Set environment variable
    os.environ['DATABASE_TARGET'] = target
    
    # Get database configuration
    env_config = get_database_config()
    db_config = env_config.get_database_config()
    
    print(f"  Host: {db_config['host']}:{db_config['port']}")
    print(f"  User: {db_config['user']}")
    
    try:
        # Connect to database
        connection = mysql.connector.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        
        cursor = connection.cursor()
        
        # Expected databases and their tables
        expected_databases = {
            db_config['agents_name']: [
                'agents', 'agent_experiences', 'agent_personal_summaries',
                'l2_agent_core', 'l2_geo', 'l2_location', 
                'l2_other_part_1', 'l2_other_part_2', 'l2_other_part_3', 'l2_other_part_4',
                'l2_political_part_1', 'l2_political_part_2', 'l2_political_part_3'
            ],
            db_config['firms_name']: ['firms', 'firm_states'],
            db_config['sim_name']: [
                'simulations', 'action_ledger', 'events', 'transactions',
                'plans', 'plan_steps', 'fact_gdp_periods'
            ]
        }
        
        all_good = True
        
        for db_name, expected_tables in expected_databases.items():
            print(f"\n  Database: {db_name}")
            try:
                cursor.execute(f"USE {db_name}")
                cursor.execute("SHOW TABLES")
                actual_tables = [row[0] for row in cursor.fetchall()]
                
                print(f"    Tables found: {len(actual_tables)}")
                
                # Check each expected table
                missing_tables = []
                for expected_table in expected_tables:
                    if expected_table in actual_tables:
                        print(f"    [SUCCESS] {expected_table}")
                    else:
                        print(f"    [MISSING] {expected_table} - MISSING")
                        missing_tables.append(expected_table)
                        all_good = False
                
                if missing_tables:
                    print(f"    [WARNING] Missing {len(missing_tables)} tables: {missing_tables}")
                else:
                    print(f"    [SUCCESS] All {len(expected_tables)} tables present")
                    
            except Exception as e:
                print(f"    [ERROR] Error checking {db_name}: {e}")
                all_good = False
        
        if all_good:
            print(f"\n[SUCCESS] All tables verified successfully on {target.upper()}!")
        else:
            print(f"\n[ERROR] Some tables are missing on {target.upper()}!")
        
        return all_good
        
    except Exception as e:
        print(f"[ERROR] Failed to connect to {target.upper()}: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Verify World_Sim database tables")
    parser.add_argument("--target", choices=['docker', 'nas', 'both'], 
                       default='both', help="Target to verify")
    args = parser.parse_args()
    
    if args.target == 'both':
        print("VERIFYING DATABASE TABLES ON BOTH TARGETS")
        print("=" * 60)
        
        # Verify Docker
        print("\n1. Verifying Docker...")
        docker_ok = verify_database_tables('docker')
        
        # Verify NAS
        print("\n2. Verifying NAS...")
        nas_ok = verify_database_tables('nas')
        
        print("\n" + "=" * 60)
        if docker_ok and nas_ok:
            print("[SUCCESS] ALL TABLES VERIFIED SUCCESSFULLY ON BOTH TARGETS!")
        else:
            print("[ERROR] SOME TABLES ARE MISSING - CHECK ABOVE FOR DETAILS")
        
    else:
        verify_database_tables(args.target)

if __name__ == "__main__":
    main()

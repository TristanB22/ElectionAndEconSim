#!/usr/bin/env python3
"""
Drop World_Sim databases script
Drops all world_sim databases on both NAS and Docker targets.
"""
import sys
import os
import argparse
from pathlib import Path

from Utils.path_manager import initialize_paths
initialize_paths()

from Database.connection_manager import get_db_manager, execute_query


def drop_databases(target):
    """Drop all world_sim databases for the specified target."""
    print(f"Dropping databases on {target.upper()}...")
    
    # Set environment variable
    os.environ['DATABASE_TARGET'] = target
    
    # Get database configuration
    env_config = EnvironmentConfig()
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
        
        # Drop databases
        databases = [db_config['agents_name'], db_config['firms_name'], db_config['sim_name']]
        
        for db_name in databases:
            try:
                cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
                print(f"  [SUCCESS] Dropped database: {db_name}")
            except Exception as e:
                print(f"  [WARNING] Error dropping {db_name}: {e}")
        
        connection.commit()
        print(f"[SUCCESS] Successfully dropped databases on {target.upper()}")
        
    except Exception as e:
        print(f"[ERROR] Failed to connect to {target.upper()}: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()
    
    return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Drop World_Sim databases")
    parser.add_argument("--target", choices=['docker', 'nas', 'both'], 
                       default='both', help="Target to drop databases on")
    args = parser.parse_args()
    
    if args.target == 'both':
        print("DROPPING DATABASES ON BOTH TARGETS")
        print("=" * 50)
        
        # Drop on Docker
        print("\n1. Dropping on Docker...")
        drop_databases('docker')
        
        # Drop on NAS
        print("\n2. Dropping on NAS...")
        drop_databases('nas')
        
        print("\n[SUCCESS] All databases dropped!")
        
    else:
        drop_databases(args.target)

if __name__ == "__main__":
    main()

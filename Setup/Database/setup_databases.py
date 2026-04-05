#!/usr/bin/env python3
"""
Database Setup Script - SQL File Based
Creates and populates the world_sim databases using SQL files.
"""
import sys
import os
import argparse
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Utils.environment_config import get_database_config
from sql_executor import get_database_connection, execute_sql_files_in_order, insert_l2_test_data

def add_test_data(connection, db_config):
    """Add test data to databases."""
    print("Adding test data...")
    
    cursor = connection.cursor()
    
    try:
        # Add test firm data
        print("  Adding test firm data...")
        cursor.execute(f"USE {db_config['firms_name']}")
        cursor.execute("""
            INSERT INTO firms (
                id, company_name, industry_code, address, year, dunsno, nationalcode, countycode, 
                statecode, citycode, streetaddress, city, state, zipcode, zipcode4, mailingaddresscode,
                mailingaddress, mailingcityname, mailingstate, mailingzipcode, mailingzipcode4,
                phonenumber, principal, ddm, businessdescription, yearstarted, sls, slscode,
                employeesthissite, employeesthissitecode, employeesallsites, employeesallsitescode,
                sic1, sic2, sic3, sic4, sic5, sic6, secondaryname, parentcityname, parentstate,
                dandboffice, hqdunsno, parentdunsno, ultdunsno, status, subsidiaryindicator,
                manufacturing, salesgrowth, employmentgrowth, smsacode, baseyearsales,
                baseyearemployment, trendyearsales, trendyearemployment, populationcode,
                transactioncode, hiercode, diascode, reportdate
            ) VALUES (
                'test_firm_001', 'Test Manufacturing Corp', '311', '123 Industrial Blvd', 2023, '123456789', 
                'US123456789', '001', 'CA', '12345', '123 Industrial Blvd', 'Los Angeles', 'CA', '90210', 
                '1234', '001', '123 Industrial Blvd', 'Los Angeles', 'CA', '90210', '1234', 
                '555-123-4567', 'John Smith', 'Jane Doe', 'Manufacturing of electronic components', 1995, 
                5000000.00, '1', 25, '1', 50, '1', '3571', '3572', '3573', '3574', '3575', '3576', 
                'TMC Corp', 'Los Angeles', 'CA', '001', '123456789', '123456789', '123456789', 
                'Active', 'N', 'Y', 0.05, 0.02, '31080', 4500000.00, 45, 5000000.00, 50, '1', '1', '1', '1', '2023-12-31'
            )
        """)
        
        # Add test simulation data
        print("  Adding test simulation data...")
        cursor.execute(f"USE {db_config['sim_name']}")
        cursor.execute("""
            INSERT INTO simulations (
                simulation_id, started_by, description, status, parameters, results,
                simulation_start_datetime, current_simulation_datetime, simulation_end_datetime,
                tick_granularity, config_json
            ) VALUES (
                'test_sim_001', 'test_user', 'Test simulation for development', 'completed',
                '{"agents": 10, "firms": 5}', '{"gdp": 1000000, "transactions": 500}',
                '2023-01-01 09:00:00', '2023-01-01 17:00:00', '2023-01-01 17:00:00',
                '15m', '{"tick_duration": 15, "max_ticks": 32}'
            )
        """)
        
        connection.commit()
        print("  [SUCCESS] Test data added successfully")
        
    except Exception as e:
        print(f"  [ERROR] Error adding test data: {e}")
        raise
    finally:
        cursor.close()


def verify_databases(connection, db_config, databases_to_setup):
    """Verify that specified databases and tables were created successfully."""
    print("\nVerification:")
    print("=" * 50)
    
    cursor = connection.cursor()
    
    # Map database types to actual names
    db_name_map = {
        'agents': db_config['agents_name'],
        'firms': db_config['firms_name'],
        'simulations': db_config['sim_name'],
        'geo': db_config['geo_name']
    }
    
    databases_to_verify = [db_name_map[db_type] for db_type in databases_to_setup]
    
    for db_name in databases_to_verify:
        try:
            cursor.execute(f"USE {db_name}")
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            print(f"{db_name}: {tables}")
        except Exception as e:
            print(f"[ERROR] Error verifying {db_name}: {e}")
    
    cursor.close()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Setup world_sim databases using SQL files")
    parser.add_argument("--target", choices=['docker', 'nas'], help="Database target (overrides DATABASE_TARGET env var)")
    parser.add_argument("--test-data", action="store_true", help="Load test data")
    
    # Database selection group
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--simulation", action="store_true", help="Setup simulation databases (agents, firms, simulations)")
    group.add_argument("--geo", action="store_true", help="Setup geo database only")
    group.add_argument("--all", action="store_true", help="Setup all databases (agents, firms, simulations, geo)")
    
    args = parser.parse_args()
    
    # # Check for deprecated options that are no longer supported
    # if args.geo:
    #     print("ERROR: --geo option is no longer supported!")
    #     print("   The geo database now uses PostGIS on the remote NAS.")
    #     print("   The old MySQL schema (10_geo_pois.sql) cannot be used.")
    #     print("   PostGIS is already set up and configured in your .env file.")
    #     print("   Use the PostGIS connection settings to access spatial data.")
    #     print()
    #     print("   PostGIS connection info:")
    #     print("   - Host: 192.168.0.164:5432")
    #     print("   - Database: world_sim_geo")
    #     print("   - User: postgres")
    #     print("   - See .env file for full configuration")
    #     sys.exit(1)
    
    # if args.all:
    #     print("ERROR: --all option is no longer supported!")
    #     print("   The geo database now uses PostGIS on the remote NAS.")
    #     print("   The old MySQL schema (10_geo_pois.sql) cannot be used.")
    #     print("   PostGIS is already set up and configured in your .env file.")
    #     print()
    #     print("   To setup simulation databases only, use:")
    #     print("   python setup_databases.py --simulation")
    #     print()
    #     print("   For geo data, use the PostGIS connection settings:")
    #     print("   - Host: 192.168.0.164:5432")
    #     print("   - Database: world_sim_geo")
    #     print("   - User: postgres")
    #     print("   - See .env file for full configuration")
    #     sys.exit(1)
    
    # Set environment variable if provided
    if args.target:
        os.environ['DATABASE_TARGET'] = args.target
    
    # Get database configuration
    db_config = get_database_config()
    
    # Determine which databases to setup
    if args.simulation:
        databases_to_setup = ['agents', 'firms', 'simulations']
        setup_type = "SIMULATION DATABASES"
    elif args.geo:
        databases_to_setup = ['geo']
        setup_type = "GEO DATABASE"
    elif args.all:
        databases_to_setup = ['agents', 'firms', 'simulations', 'geo']
        setup_type = "ALL DATABASES"
    
    print("WORLD_SIM DATABASE SETUP")
    print(f"Setup Type: {setup_type}")
    print(f"Target: {db_config['target'].upper()}")
    print(f"Host: {db_config['host']}:{db_config['port']}")
    print(f"User: {db_config['user']}")
    print(f"Test Data: {'Yes' if args.test_data else 'No'}")
    print(f"Databases: {', '.join(databases_to_setup)}")
    print()
    
    try:
        # Get database connection
        connection = get_database_connection()
        
        # Setup databases using sql_executor
        schema_dir = Path(__file__).parent / "schemas"
        
        if args.geo:
            # Setup geo database only
            print("Setting up geo database...")
            success = execute_sql_files_in_order(connection, schema_dir, False, include_geo=True, only_geo=True)
        elif args.simulation:
            # Setup simulation databases only
            print("Setting up simulation databases...")
            success = execute_sql_files_in_order(connection, schema_dir, args.test_data, include_geo=False, only_geo=False)
        elif args.all:
            # Setup all databases including geo
            print("Setting up all databases...")
            success = execute_sql_files_in_order(connection, schema_dir, args.test_data, include_geo=True, only_geo=False)
        
        if not success:
            print("[ERROR] Database setup failed")
            sys.exit(1)
        
        # Add test data if requested (only for simulation databases)
        if args.test_data and (args.simulation or args.all):
            add_test_data(connection, db_config)
            
            # Load L2 test data if requested (only for simulation databases)
            print("  Loading L2 test data...")
            insert_l2_test_data(connection, schema_dir)
        
        # Verify setup
        verify_databases(connection, db_config, databases_to_setup)
        
        print("\n[SUCCESS] Database setup completed successfully!")
        
    except Exception as e:
        print(f"[ERROR] Setup failed: {e}")
        sys.exit(1)
    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()

if __name__ == '__main__':
    main()
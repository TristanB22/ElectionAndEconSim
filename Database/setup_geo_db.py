#!/usr/bin/env python3
"""
Setup script for World Sim Geo Database
Creates database, tables, and migrates POI data
"""

import asyncio
import subprocess
import sys
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_postgresql():
    """Check if PostgreSQL is running and accessible."""
    try:
        result = subprocess.run(['psql', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"PostgreSQL found: {result.stdout.strip()}")
            return True
        else:
            logger.error("PostgreSQL not found")
            return False
    except FileNotFoundError:
        logger.error("PostgreSQL not installed or not in PATH")
        return False

def create_database():
    """Create the world_sim_geo database."""
    try:
        # Check if database exists
        result = subprocess.run([
            'psql', '-lqt', '-d', 'postgres'
        ], capture_output=True, text=True)
        
        if 'world_sim_geo' in result.stdout:
            logger.info("Database 'world_sim_geo' already exists")
            return True
        
        # Create database
        result = subprocess.run([
            'createdb', 'world_sim_geo'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Database 'world_sim_geo' created successfully")
            return True
        else:
            logger.error(f"Failed to create database: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False

def install_postgis():
    """Install PostGIS extension."""
    try:
        result = subprocess.run([
            'psql', '-d', 'world_sim_geo', '-c', 'CREATE EXTENSION IF NOT EXISTS postgis;'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("PostGIS extension installed successfully")
            return True
        else:
            logger.error(f"Failed to install PostGIS: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error installing PostGIS: {e}")
        return False

async def setup_database():
    """Set up the complete database with tables and data."""
    from Database.geo_database_manager import GeoDatabaseManager
    from Database.migrate_pois_to_db import migrate_maine_pois, verify_migration
    
    db_manager = GeoDatabaseManager()
    
    try:
        # Initialize database connection
        await db_manager.initialize()
        logger.info("Database connection established")
        
        # Create tables
        await db_manager.create_tables()
        logger.info("Database tables created")
        
        # Migrate POI data
        await migrate_maine_pois()
        
        # Verify migration
        await verify_migration()
        
        logger.info("Database setup completed successfully!")
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise
    finally:
        await db_manager.close()

def main():
    """Main setup function."""
    logger.info("Starting World Sim Geo Database setup")
    
    # Check prerequisites
    if not check_postgresql():
        logger.error("PostgreSQL is required but not found")
        sys.exit(1)
    
    # Create database
    if not create_database():
        logger.error("Failed to create database")
        sys.exit(1)
    
    # Install PostGIS
    if not install_postgis():
        logger.error("Failed to install PostGIS")
        sys.exit(1)
    
    # Set up database with tables and data
    try:
        asyncio.run(setup_database())
        logger.info("Setup completed successfully!")
        logger.info("You can now use the geo API endpoints")
        logger.info("Start the API server with: uvicorn Reporting.api:app --reload")
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

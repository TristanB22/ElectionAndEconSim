#!/usr/bin/env python3
"""
Backend server runner for the api that we have
"""

import os
import sys
from pathlib import Path

# add the world_sim directory to the python path
world_sim_path = Path(__file__).parent.parent
sys.path.insert(0, str(world_sim_path))

# change to the world_sim directory
os.chdir(world_sim_path)

def run():
    """
    Main entry point to just be able to start the backend server that we want to work with. 
    """
    
    print("Starting the backend server that we want to work with...")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[0]}")
    
    # print that we are using the postgis database
    print("Using the postgis database")

    try:
        # import the api so that we can run it
        # with this script
        from Reporting.api import app
        import uvicorn
        
        print("Successfully imported API module")
        print("Starting server on http://localhost:8000")
        print("API Documentation available at http://localhost:8000/docs")
        print("Press Ctrl+C to stop the server")
        print("-" * 50)
        
        # run the server
        uvicorn.run(
            "Reporting.api:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["Reporting", "Database", "Maps"],
            log_level="info"
        )
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure this is run from the correct directory")
        print("Check that all dependencies are installed")
        sys.exit(1)
        
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
#!/usr/bin/env python3
"""
Centralized Path Management System
Handles all path resolution, sys.path management, and project structure navigation.
Replaces scattered path management code throughout the codebase.
"""

import os
import sys
from pathlib import Path
import logging

def initialize_paths():
    """
    Initializes the Python path to include the project's root directory.
    This function is designed to be called from within any module of the application
    to ensure that all modules can be imported correctly.
    """
    # The project root is assumed to be the 'World_Sim' directory.
    # This is determined by going up two levels from the current file's directory.
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Configure logging levels based on VERBOSITY
    verbosity = int(os.getenv('VERBOSITY', '3'))
    if verbosity == 0:
        # At verbosity 0, only show WARNING and above (suppress INFO)
        logging.getLogger().setLevel(logging.WARNING)
        # Specifically silence Database loggers that spam INFO messages
        logging.getLogger('Database.managers.base').setLevel(logging.WARNING)
        logging.getLogger('Database.config').setLevel(logging.WARNING)
        logging.getLogger('Database.managers.simulations').setLevel(logging.WARNING)
    elif verbosity == 1:
        logging.getLogger().setLevel(logging.INFO)
    else:
        # verbosity >= 2: default INFO level
        logging.getLogger().setLevel(logging.INFO)

def get_project_root() -> Path:
    """
    Returns the project's root directory.
    """
    return Path(__file__).resolve().parents[1]

#!/usr/bin/env python3
"""
Centralized Environment Variable Loader
Handles all environment variable loading patterns used throughout the codebase.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Global flag to track if environment has been loaded
_env_loaded = False
_loaded_paths = set()

def _find_env_file(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find .env file starting from the given path or current working directory.

    Args:
        start_path: Path to start searching from. If None, uses current file location.

    Returns:
        Path to .env file if found, None otherwise.
    """
    if start_path is None:
        # Start from current file's directory
        start_path = Path(__file__).resolve().parent

    # Try different relative paths from common starting points
    search_paths = [
        start_path / '.env',  # Current directory
        start_path.parent / '.env',  # Parent directory
        start_path.parents[1] / '.env',  # Two levels up
        start_path.parents[2] / '.env',  # Three levels up (common for World_Sim)
        Path.cwd() / '.env',  # Current working directory
    ]

    for env_path in search_paths:
        if env_path.exists() and env_path.is_file():
            return env_path

    return None

def _load_dotenv_with_fallback(env_path: Optional[Path] = None, override: bool = False) -> bool:
    """
    Load environment variables with proper error handling.

    Args:
        env_path: Specific path to .env file. If None, searches automatically.
        override: Whether to override existing environment variables.

    Returns:
        bool: True if loaded successfully, False otherwise.
    """
    try:
        from dotenv import load_dotenv

        if env_path is None:
            env_path = _find_env_file()

        if env_path and env_path.exists():
            load_dotenv(dotenv_path=env_path, override=override)
            _loaded_paths.add(str(env_path))
            return True
        else:
            # Fallback to basic loading without path (looks in current directory)
            load_dotenv(override=override)
            return True

    except ImportError:
        # python-dotenv not available - this is handled gracefully
        return False
    except Exception as e:
        print(f"Warning: Error loading environment variables: {e}")
        return False

def load_environment(env_path: Optional[Path] = None, override: bool = False) -> bool:
    """
    Centralized environment variable loading function.

    This replaces all the scattered environment loading code throughout the codebase.

    Args:
        env_path: Specific path to .env file. If None, searches automatically.
        override: Whether to override existing environment variables.

    Returns:
        bool: True if loaded successfully, False otherwise.

    Usage:
        # Simple usage (replaces basic load_dotenv())
        from Utils.env_loader import load_environment
        load_environment()

        # With specific path (replaces path-based loading)
        load_environment(Path(__file__).resolve().parents[2] / '.env')

        # With override (replaces override=True usage)
        load_environment(override=True)
    """
    global _env_loaded

    # If already loaded and not overriding, return success
    if _env_loaded and not override:
        return True

    success = _load_dotenv_with_fallback(env_path, override)

    if success:
        _env_loaded = True

    return success

def get_env_path(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Get the path to the .env file that would be loaded.

    Args:
        start_path: Path to start searching from. If None, uses current file location.

    Returns:
        Path to .env file if found, None otherwise.
    """
    return _find_env_file(start_path)

def is_environment_loaded() -> bool:
    """
    Check if environment variables have been loaded.

    Returns:
        bool: True if environment has been loaded.
    """
    return _env_loaded

def get_loaded_paths() -> set:
    """
    Get the paths of .env files that have been loaded.

    Returns:
        set: Set of paths that have been loaded.
    """
    return _loaded_paths.copy()

def reset_environment() -> None:
    """
    Reset the environment loading state. Useful for testing.
    """
    global _env_loaded, _loaded_paths
    _env_loaded = False
    _loaded_paths.clear()

# Backward compatibility - provide the old pattern but centralized
def load_env_file(env_path: Optional[str] = None) -> None:
    """
    Backward compatibility function for existing code.

    Args:
        env_path: String path to .env file.
    """
    if env_path:
        load_environment(Path(env_path))
    else:
        load_environment()

# Auto-load environment on module import (for backward compatibility)
# Ensures that existing code that just does 'from dotenv import load_dotenv; load_dotenv()'
# will still work, but through our centralized system
if not _env_loaded:
    load_environment()

#!/usr/bin/env python3
"""
Database Target Switcher
Simple script to switch between Docker and NAS database configurations.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_file = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(env_file)

def switch_to_docker():
    """Switch to Docker configuration."""
    print("Switching to Docker configuration...")
    
    # Read current .env file
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Update DATABASE_TARGET, SERVICE_TARGET and ensure QDRANT_TARGET is docker
    updated_lines = []
    for line in lines:
        if line.startswith('DATABASE_TARGET='):
            updated_lines.append('DATABASE_TARGET=docker\n')
        elif line.startswith('SERVICE_TARGET='):
            updated_lines.append('SERVICE_TARGET=docker\n')
        elif line.startswith('QDRANT_TARGET='):
            updated_lines.append('QDRANT_TARGET=docker\n')
        else:
            updated_lines.append(line)
    
    # Write updated .env file
    with open(env_file, 'w') as f:
        f.writelines(updated_lines)
    
    # Reset database manager to pick up new configuration
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(project_root))
        from Database.config import reset_database_manager
        reset_database_manager()
        print("[INFO] Reset database manager")
    except Exception as e:
        print(f"[WARNING] Could not reset database manager: {e}")
    
    print("[SUCCESS] Switched to Docker configuration")
    print("   Database: localhost:1001")
    print("   Qdrant: localhost:1002")
    print("   phpMyAdmin: http://localhost:1005")
    print("   Grafana: http://localhost:1006")

def switch_to_nas():
    """Switch to NAS configuration."""
    print("Switching to NAS configuration...")
    
    # Read current .env file
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Update DATABASE_TARGET and SERVICE_TARGET but keep QDRANT_TARGET as docker (local)
    updated_lines = []
    for line in lines:
        if line.startswith('DATABASE_TARGET='):
            updated_lines.append('DATABASE_TARGET=nas\n')
        elif line.startswith('SERVICE_TARGET='):
            updated_lines.append('SERVICE_TARGET=nas\n')
        elif line.startswith('QDRANT_TARGET='):
            updated_lines.append('QDRANT_TARGET=docker\n')  # Always keep Qdrant local
        else:
            updated_lines.append(line)
    
    # Write updated .env file
    with open(env_file, 'w') as f:
        f.writelines(updated_lines)
    
    # Reset database manager to pick up new configuration
    try:
        import sys
        from pathlib import Path
        project_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(project_root))
        from Database.config import reset_database_manager
        reset_database_manager()
        print("[INFO] Reset database manager")
    except Exception as e:
        print(f"[WARNING] Could not reset database manager: {e}")
    
    print("[SUCCESS] Switched to NAS configuration")
    print("   Database: 192.168.0.164:3306")
    print("   Qdrant: localhost:1002 (kept local)")
    print("   phpMyAdmin: http://192.168.0.164:8888")
    print("   Grafana: http://192.168.0.164:3000")

def show_current_config():
    """Show current configuration."""
    # Add project root to path
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))
    
    from Utils.environment_config import EnvironmentConfig
    
    print("Current Configuration:")
    print("=" * 40)
    
    try:
        env_config = EnvironmentConfig()
        env_config.print_config_summary()
    except Exception as e:
        print(f"[ERROR] Error reading configuration: {e}")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python switch_database_target.py [docker|nas|status]")
        print()
        print("Commands:")
        print("  docker  - Switch to Docker configuration")
        print("  nas     - Switch to NAS configuration")
        print("  status  - Show current configuration")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'docker':
        switch_to_docker()
    elif command == 'nas':
        switch_to_nas()
    elif command == 'status':
        show_current_config()
    else:
        print(f"[ERROR] Unknown command: {command}")
        print("Use 'docker', 'nas', or 'status'")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Environment Configuration Helper
Handles selection between Docker and NAS configurations based on environment variables.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
# Load environment variables using centralized loader
try:
    from Utils.env_loader import load_environment
    # Load from World_Sim root (parents[1])
    env_path = Path(__file__).resolve().parents[1] / '.env'
    load_environment(env_path)
except ImportError:
    # Fallback to basic dotenv loading if centralized loader not available
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')

class EnvironmentConfig:
    """Handles environment-based configuration selection."""
    
    def __init__(self):
        """Initialize the configuration helper."""
        self.database_target = os.getenv('DATABASE_TARGET', 'docker').lower()
        self.qdrant_target = os.getenv('QDRANT_TARGET', 'docker').lower()
        self.service_target = os.getenv('SERVICE_TARGET', 'docker').lower()
        
        # Validate targets
        valid_targets = ['docker', 'nas']
        if self.database_target not in valid_targets:
            raise ValueError(f"Invalid DATABASE_TARGET: {self.database_target}. Must be 'docker' or 'nas'")
        if self.qdrant_target not in valid_targets:
            raise ValueError(f"Invalid QDRANT_TARGET: {self.qdrant_target}. Must be 'docker' or 'nas'")
        if self.service_target not in valid_targets:
            raise ValueError(f"Invalid SERVICE_TARGET: {self.service_target}. Must be 'docker' or 'nas'")
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration based on DATABASE_TARGET."""
        if self.database_target == 'docker':
            return {
                'host': os.getenv('DB_HOST_DOCKER', 'localhost'),
                'port': int(os.getenv('DB_PORT_DOCKER', '1001')),
                'user': os.getenv('DB_USER_DOCKER', 'root'),
                'password': os.getenv('DB_PASSWORD_DOCKER', 'world_sim_dev'),
                'agents_name': os.getenv('DB_AGENTS_NAME', 'world_sim_agents'),
                'firms_name': os.getenv('DB_FIRMS_NAME', 'world_sim_firms'),
                'sim_name': os.getenv('DB_SIM_NAME', 'world_sim_simulations'),
                'geo_name': os.getenv('DB_GEO_NAME', 'world_sim_geo'),
                'target': 'docker'
            }
        elif self.database_target == 'nas':
            return {
                'host': os.getenv('DB_HOST_NAS', '192.168.0.164'),
                'port': int(os.getenv('DB_PORT_NAS', '3306')),
                'user': os.getenv('DB_USER_NAS', 'root'),
                'password': os.getenv('DB_PASSWORD_NAS', ''),
                'agents_name': os.getenv('DB_AGENTS_NAME', 'world_sim_agents'),
                'firms_name': os.getenv('DB_FIRMS_NAME', 'world_sim_firms'),
                'sim_name': os.getenv('DB_SIM_NAME', 'world_sim_simulations'),
                'geo_name': os.getenv('DB_GEO_NAME', 'world_sim_geo'),
                'target': 'nas'
            }
        else:
            raise ValueError(f"Invalid database target: {self.database_target}")
    
    def get_qdrant_config(self) -> Dict[str, Any]:
        """Get Qdrant configuration based on QDRANT_TARGET."""
        if self.qdrant_target == 'docker':
            return {
                'host': os.getenv('QDRANT_HOST_DOCKER', 'localhost'),
                'port': int(os.getenv('QDRANT_PORT_DOCKER', '1002')),
                'grpc_port': int(os.getenv('QDRANT_GRPC_PORT_DOCKER', '1003')),
                'target': 'docker'
            }
        elif self.qdrant_target == 'nas':
            return {
                'host': os.getenv('QDRANT_HOST_NAS', '192.168.0.164'),
                'port': int(os.getenv('QDRANT_PORT_NAS', '6333')),
                'grpc_port': int(os.getenv('QDRANT_GRPC_PORT_NAS', '6334')),
                'target': 'nas'
            }
        else:
            raise ValueError(f"Invalid Qdrant target: {self.qdrant_target}")
    
    def get_service_config(self) -> Dict[str, Any]:
        """Get service configuration based on SERVICE_TARGET."""
        if self.service_target == 'docker':
            return {
                'phpmyadmin_url': os.getenv('PHPMYADMIN_URL_DOCKER', 'http://localhost:1005'),
                'grafana_url': os.getenv('GRAFANA_URL_DOCKER', 'http://localhost:1006'),
                'grafana_user': os.getenv('GRAFANA_USER_DOCKER', 'admin'),
                'grafana_password': os.getenv('GRAFANA_PASSWORD_DOCKER', 'admin'),
                'target': 'docker'
            }
        elif self.service_target == 'nas':
            return {
                'phpmyadmin_url': os.getenv('PHPMYADMIN_URL_NAS', 'http://192.168.0.164:8888'),
                'grafana_url': os.getenv('GRAFANA_URL_NAS', 'http://192.168.0.164:3000'),
                'grafana_user': os.getenv('GRAFANA_USER_NAS', 'admin'),
                'grafana_password': os.getenv('GRAFANA_PASSWORD_NAS', 'admin'),
                'target': 'nas'
            }
        else:
            raise ValueError(f"Invalid service target: {self.service_target}")
    
    def get_legacy_config(self) -> Dict[str, Any]:
        """Get legacy configuration for backward compatibility."""
        db_config = self.get_database_config()
        return {
            'DB_HOST': db_config['host'],
            'DB_PORT': db_config['port'],
            'DB_USER': db_config['user'],
            'DB_PASSWORD': db_config['password'],
            'DB_NAME': db_config['agents_name'],
            'DB_AGENTS_NAME': db_config['agents_name'],
            'DB_FIRMS_NAME': db_config['firms_name'],
            'DB_SIM_NAME': db_config['sim_name']
        }
    
    def print_config_summary(self):
        """Print a summary of the current configuration."""
        print("Environment Configuration Summary")
        print("=" * 50)
        
        db_config = self.get_database_config()
        qdrant_config = self.get_qdrant_config()
        service_config = self.get_service_config()
        
        print(f"Database Target: {self.database_target.upper()}")
        print(f"   Host: {db_config['host']}:{db_config['port']}")
        print(f"   User: {db_config['user']}")
        print(f"   Databases: {db_config['agents_name']}, {db_config['firms_name']}, {db_config['sim_name']}")
        
        print(f"\nQdrant Target: {self.qdrant_target.upper()}")
        print(f"   Host: {qdrant_config['host']}:{qdrant_config['port']}")
        print(f"   gRPC Port: {qdrant_config['grpc_port']}")
        
        print(f"\nService Target: {self.service_target.upper()}")
        print(f"   phpMyAdmin: {service_config['phpmyadmin_url']}")
        print(f"   Grafana: {service_config['grafana_url']}")
        
        print("=" * 50)

# Global instance for easy access
env_config = EnvironmentConfig()

def get_database_config() -> Dict[str, Any]:
    """Get database configuration."""
    return env_config.get_database_config()

def get_qdrant_config() -> Dict[str, Any]:
    """Get Qdrant configuration."""
    return env_config.get_qdrant_config()

def get_service_config() -> Dict[str, Any]:
    """Get service configuration."""
    return env_config.get_service_config()

def get_legacy_config() -> Dict[str, Any]:
    """Get legacy configuration for backward compatibility."""
    return env_config.get_legacy_config()

if __name__ == "__main__":
    # Print configuration summary when run directly
    env_config.print_config_summary()


#!/usr/bin/env python3
"""
Centralized Database Configuration and Management for World_Sim

Single source of truth for all database operations.
All database-related environment variables are loaded here.
"""

from __future__ import annotations

import os
from pathlib import Path
import threading
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Load .env early so all scripts (including standalone ones) pick up DB config
try:
    from dotenv import load_dotenv  # type: ignore
    # Load World_Sim/.env (this file is at World_Sim/Database/config.py)
    _env_path = Path(__file__).resolve().parents[1] / '.env'
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
except Exception:
    # Non-fatal if dotenv isn't installed or .env missing; environment vars may be set by shell
    pass

# Try importing mysql connector
try:
    from mysql.connector import pooling
    from mysql.connector import Error as MySQLError
    MYSQL_AVAILABLE = True
except ImportError:
    logger.warning("mysql-connector-python not available")
    pooling = None
    MySQLError = Exception
    MYSQL_AVAILABLE = False


@dataclass
class DatabaseConfig:
    """
    Pure data container for database configuration.
    Does NOT load environment variables - that's DatabaseManager's job.
    """
    host: str
    port: int
    user: str
    password: str
    database: str
    target: str
    pool_size: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    max_connections: int = 50
    connection_timeout: int = 10
    query_timeout: int = 30
    autocommit: bool = True
    charset: str = 'utf8mb4'
    collation: str = 'utf8mb4_unicode_ci'
    insertion_batch_size: int = 50000


class DatabaseManager:
    """
    Centralized database manager using singleton pattern.
    This is the ONLY place where database configuration is loaded from environment variables.
    """
    
    _instance: Optional['DatabaseManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Private constructor. Use get_instance() instead."""
        if not MYSQL_AVAILABLE:
            raise ImportError("mysql-connector-python is required. Install with: pip install mysql-connector-python")
        
        self.pools: Dict[str, pooling.MySQLConnectionPool] = {}
        self._config = self._load_configurations_from_env()
        self._initialize_pools()
    
    @classmethod
    def get_instance(cls) -> 'DatabaseManager':
        """
        Get the singleton instance of DatabaseManager.
        This is the ONLY way to access the database manager.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance.
        Useful for testing or when configuration changes.
        """
        with cls._lock:
            if cls._instance is not None:
                # Close all pools
                try:
                    for pool in cls._instance.pools.values():
                        # Pools don't have a close method, but connections do
                        pass
                except Exception as e:
                    logger.warning(f"Error closing pools during reset: {e}")
            cls._instance = None
            # Immediately create new instance
            cls._instance = cls()
    
    def _load_configurations_from_env(self) -> DatabaseConfig:
        """
        Load database configuration via EnvironmentConfig (same source as switch script).
        """
        try:
            from Utils.environment_config import EnvironmentConfig  # unified status/target logic
            env_cfg = EnvironmentConfig().get_database_config()
            target = env_cfg.get('target', 'docker')
            config = DatabaseConfig(
                host=str(env_cfg.get('host', 'localhost')),
                port=int(env_cfg.get('port', 1001)),
                user=str(env_cfg.get('user', 'root')),
                password=str(env_cfg.get('password', '')),
                database=str(env_cfg.get('agents_name', 'world_sim_agents')),
                target=target,
                pool_size=int(os.getenv('DB_POOL_SIZE', '10')),
                pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30')),
                pool_recycle=int(os.getenv('DB_POOL_RECYCLE', '3600')),
                max_connections=int(os.getenv('DB_MAX_CONNECTIONS', '50')),
                connection_timeout=int(os.getenv('DB_CONNECTION_TIMEOUT', '10')),
                query_timeout=int(os.getenv('DB_QUERY_TIMEOUT', '30')),
                insertion_batch_size=int(os.getenv('DB_INSERT_BATCH_SIZE', '50000'))
            )
            logger.info(f"Loaded database configuration for target: {target}")
            return config
        except Exception as e:
            logger.error(f"EnvironmentConfig fallback to raw env due to error: {e}")
            # Fallback to previous env-based logic
            target = os.getenv('DATABASE_TARGET', 'docker').lower()
            if target == 'nas':
                return DatabaseConfig(
                    host=os.getenv('DB_HOST_NAS', '192.168.0.164'),
                    port=int(os.getenv('DB_PORT_NAS', '3306')),
                    user=os.getenv('DB_USER_NAS', 'root'),
                    password=os.getenv('DB_PASSWORD_NAS', ''),
                    database=os.getenv('DB_AGENTS_NAME', 'world_sim_agents'),
                    target='nas'
                )
            else:
                return DatabaseConfig(
                    host=os.getenv('DB_HOST_DOCKER', 'localhost'),
                    port=int(os.getenv('DB_PORT_DOCKER', '1001')),
                    user=os.getenv('DB_USER_DOCKER', 'root'),
                    password=os.getenv('DB_PASSWORD_DOCKER', 'world_sim_dev'),
                    database=os.getenv('DB_AGENTS_NAME', 'world_sim_agents'),
                    target='docker'
                )
    
    def _initialize_pools(self):
        """Initialize connection pools for all databases."""
        # Check if we should skip optional databases (useful for multiprocessing workers)
        skip_optional = os.getenv('SKIP_OPTIONAL_DB_POOLS', '0').lower() in ('1', 'true', 'yes')
        
        # Get database names from unified environment config
        try:
            from Utils.environment_config import EnvironmentConfig
            db_cfg = EnvironmentConfig().get_database_config()
            databases = [
                str(db_cfg.get('agents_name', 'world_sim_agents')),
                str(db_cfg.get('firms_name', 'world_sim_firms')),
                str(db_cfg.get('sim_name', 'world_sim_simulations')),
                str(db_cfg.get('geo_name', 'world_sim_geo')),
            ]
            # Only add ATUS database if planning is enabled
            planning_disabled = os.getenv('DISABLE_PLANNING', '0').lower() in ('1', 'true', 'yes')
            if not planning_disabled:
                databases.append(os.getenv('DB_ATUS_NAME', 'world_sim_atus'))
        except Exception:
            databases = [
                os.getenv('DB_AGENTS_NAME', 'world_sim_agents'),
                os.getenv('DB_FIRMS_NAME', 'world_sim_firms'),
                os.getenv('DB_SIM_NAME', 'world_sim_simulations'),
                os.getenv('DB_GEO_NAME', 'world_sim_geo'),
            ]
            # Only add ATUS database if planning is enabled
            planning_disabled = os.getenv('DISABLE_PLANNING', '0').lower() in ('1', 'true', 'yes')
            if not planning_disabled:
                databases.append(os.getenv('DB_ATUS_NAME', 'world_sim_atus'))
        
        # Remove duplicates while preserving order
        databases = list(dict.fromkeys(databases))
        
        # If skip_optional is set, only initialize databases that are explicitly needed
        # For census scripts, we only need the census/alternative_data databases (which aren't in this list)
        # So we skip initializing agents/firms/simulations/geo to save connections
        if skip_optional:
            # Only initialize databases that are explicitly requested via DB_REQUIRED_DBS
            required_dbs_str = os.getenv('DB_REQUIRED_DBS', '')
            if required_dbs_str:
                required_dbs = [db.strip() for db in required_dbs_str.split(',') if db.strip()]
                databases = [db for db in databases if db in required_dbs]
            else:
                # If no required databases specified, skip all optional databases
                # (census/alternative_data will be created on-demand when needed)
                databases = []
        
        for db_name in databases:
            # Retry logic for connection limit errors
            import time
            max_retries = 3
            retry_delays = [1.0, 2.0, 5.0]
            pool_created = False
            
            for attempt in range(max_retries):
                try:
                    pool_config = {
                        'host': self._config.host,
                        'port': self._config.port,
                        'user': self._config.user,
                        'password': self._config.password,
                        'database': db_name,
                        'pool_name': f"pool_{db_name}",
                        'pool_size': self._config.pool_size,
                        'pool_reset_session': True,
                        'autocommit': self._config.autocommit,
                        'charset': self._config.charset,
                        'collation': self._config.collation,
                        'connection_timeout': self._config.connection_timeout
                    }
                    
                    self.pools[db_name] = pooling.MySQLConnectionPool(**pool_config)
                    # Only log if verbosity >= 1
                    verbosity = int(os.getenv('VERBOSITY', '3'))
                    if verbosity >= 1:
                        logger.info(f"Created connection pool for '{db_name}'")
                    pool_created = True
                    break  # Success, exit retry loop
                    
                except MySQLError as e:
                    error_msg = str(e)
                    is_connection_limit = "1040" in error_msg or "Too many connections" in error_msg
                    
                    # Treat geo database as optional; warn instead of error if missing
                    optional_geo = os.getenv('DB_GEO_NAME', 'world_sim_geo')
                    is_optional = (db_name == optional_geo)
                    
                    if is_optional:
                        logger.warning(f"Optional database '{db_name}' not available: {e}")
                        break  # Don't retry optional databases
                    
                    if is_connection_limit and attempt < max_retries - 1:
                        # Retry with exponential backoff
                        delay = retry_delays[attempt]
                        logger.warning(
                            f"Connection limit reached for '{db_name}'. "
                            f"Retrying in {delay}s (attempt {attempt + 1}/{max_retries})..."
                        )
                        time.sleep(delay)
                        continue
                    
                    # Final attempt failed or non-retryable error
                    if is_connection_limit:
                        logger.error(f"Failed to create connection pool for '{db_name}' after {max_retries} attempts: {e}")
                        logger.warning(f"Will attempt on-demand pool creation for '{db_name}' when needed")
                        # Don't store anything - will be created on-demand with retry logic
                    else:
                        logger.error(f"Failed to create connection pool for '{db_name}': {e}")
                    break  # Exit retry loop
    
    def get_connection(self, db_name: str = None):
        """
        Get a connection from the appropriate pool.
        
        Args:
            db_name: Database name. If None, uses the default database.
        """
        if db_name is None:
            db_name = self._config.database
        
        if db_name not in self.pools:
            # Try to create pool on demand with smaller pool size to avoid connection exhaustion
            # Use retry logic with exponential backoff for connection limit errors
            import time
            max_retries = 3
            retry_delays = [1.0, 2.0, 5.0]  # seconds
            
            for attempt in range(max_retries):
                try:
                    # Use smaller pool size for on-demand pools to avoid hitting MySQL connection limits
                    on_demand_pool_size = min(self._config.pool_size, 2)
                    pool_config = {
                        'host': self._config.host,
                        'port': self._config.port,
                        'user': self._config.user,
                        'password': self._config.password,
                        'database': db_name,
                        'pool_name': f"pool_{db_name}",
                        'pool_size': on_demand_pool_size,
                        'pool_reset_session': True,
                        'autocommit': self._config.autocommit,
                        'charset': self._config.charset,
                        'collation': self._config.collation,
                        'connection_timeout': self._config.connection_timeout
                    }
                    
                    self.pools[db_name] = pooling.MySQLConnectionPool(**pool_config)
                    # Only log if verbosity >= 1
                    verbosity = int(os.getenv('VERBOSITY', '3'))
                    if verbosity >= 1:
                        logger.info(f"Created on-demand connection pool for '{db_name}' with size {on_demand_pool_size}")
                    break  # Success, exit retry loop
                    
                except MySQLError as e:
                    error_msg = str(e)
                    is_connection_limit = "1040" in error_msg or "Too many connections" in error_msg
                    
                    if is_connection_limit and attempt < max_retries - 1:
                        # Retry with exponential backoff
                        delay = retry_delays[attempt]
                        logger.warning(
                            f"Connection limit reached for '{db_name}'. "
                            f"Retrying in {delay}s (attempt {attempt + 1}/{max_retries})..."
                        )
                        time.sleep(delay)
                        continue
                    
                    # Final attempt failed or non-retryable error
                    if is_connection_limit:
                        logger.error(f"MySQL connection limit reached for '{db_name}' after {max_retries} attempts. Please:")
                        logger.error("  1. Close other database connections")
                        logger.error("  2. Increase MySQL max_connections setting")
                        logger.error("  3. Wait a few minutes for connections to timeout")
                        logger.error("  4. Or set DB_POOL_SIZE=1 environment variable")
                        logger.error("  5. Fall back to single connection (no pooling)")
                        
                        # Try to create a single connection as fallback (stored in a fake "pool")
                        try:
                            from mysql.connector import connect
                            single_conn = connect(
                                host=self._config.host,
                                port=self._config.port,
                                user=self._config.user,
                                password=self._config.password,
                                database=db_name,
                                autocommit=self._config.autocommit,
                                charset=self._config.charset,
                                collation=self._config.collation,
                                connection_timeout=self._config.connection_timeout
                            )
                            # Close it immediately - we'll create new ones as needed
                            single_conn.close()
                            logger.warning(f"Fallback: Will use single connections (no pool) for '{db_name}'")
                            # Store None as marker that we should use single connections
                            self.pools[db_name] = None
                            break
                        except Exception as fallback_error:
                            logger.error(f"Fallback connection also failed for '{db_name}': {fallback_error}")
                            raise ValueError(f"Failed to create pool or fallback connection for database '{db_name}': {e}")
                    else:
                        # Non-retryable error
                        raise ValueError(f"Failed to create pool for database '{db_name}': {e}")
        
        try:
            pool = self.pools[db_name]
            
            # If pool is None, we're in fallback mode - create single connections
            if pool is None:
                from mysql.connector import connect
                return connect(
                    host=self._config.host,
                    port=self._config.port,
                    user=self._config.user,
                    password=self._config.password,
                    database=db_name,
                    autocommit=self._config.autocommit,
                    charset=self._config.charset,
                    collation=self._config.collation,
                    connection_timeout=self._config.connection_timeout
                )
            
            # Normal pool mode
            return pool.get_connection()
        except MySQLError as e:
            raise ConnectionError(f"Failed to get connection for '{db_name}': {e}")
    
    def is_connected(self) -> bool:
        """Check if database manager is properly connected."""
        try:
            # Try to get a connection from any available pool
            if not self.pools:
                return False
            
            db_name = list(self.pools.keys())[0]
            conn = self.get_connection(db_name)
            conn.close()
            return True
        except Exception:
            return False
    
    def get_config(self) -> DatabaseConfig:
        """Get the current database configuration."""
        return self._config


class TableSchema:
    """Simple schema holder for database table names."""
    def __init__(self):
        # L2 Tables
        self.l2_agent_core = 'l2_agent_core'
        self.l2_location = 'l2_location'
        self.l2_geo = 'l2_geo'
        self.l2_political_part_1 = 'l2_political_part_1'
        self.l2_political_part_2 = 'l2_political_part_2'
        self.l2_political_part_3 = 'l2_political_part_3'
        self.l2_other_part_1 = 'l2_other_part_1'
        self.l2_other_part_2 = 'l2_other_part_2'
        self.l2_other_part_3 = 'l2_other_part_3'
        self.l2_other_part_4 = 'l2_other_part_4'
        
        # Agent Tables
        self.agents = 'agents'
        self.agent_summaries = 'agent_summaries'
        self.agent_memory_text = 'agent_memory_text'
        self.agent_memory_episodic = 'agent_memory_episodic'
        
        # Firm Tables
        self.firms = 'firms'
        self.firm_products = 'firm_products'
        self.firm_employees = 'firm_employees'
        
        # Simulation Tables
        self.simulations = 'simulations'
        self.simulation_agents = 'simulation_agents'
        self.simulation_firms = 'simulation_firms'
        self.simulation_events = 'simulation_events'
        self.action_ledger = 'action_ledger'
        self.transactions = 'transactions'


# Global schema instance
_schema = None

def get_schema() -> TableSchema:
    """Get the global table schema instance."""
    global _schema
    if _schema is None:
        _schema = TableSchema()
    return _schema


def get_tables() -> TableSchema:
    """Alias for get_schema() for backward compatibility."""
    return get_schema()


# Backward compatibility - legacy function names
def get_db_manager() -> DatabaseManager:
    """Legacy function. Use DatabaseManager.get_instance() instead."""
    return DatabaseManager.get_instance()


def reset_database_manager() -> None:
    """Legacy function. Use DatabaseManager.reset_instance() instead."""
    DatabaseManager.reset_instance()

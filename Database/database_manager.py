#!/usr/bin/env python3
"""
Database Manager for World_Sim

Centralized database interface with connection pooling and multiprocessing support.
"""

from __future__ import annotations

import os
import sys
import time
import logging
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple, Iterator, ContextManager
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import json
import uuid

from Utils.path_manager import initialize_paths
initialize_paths()

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

from .config import DatabaseManager, DatabaseConfig, get_tables, get_schema

import mysql.connector
from mysql.connector import pooling, Error as MySQLError
from mysql.connector.cursor import MySQLCursor

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """
    Lightweight container for query results and metadata.
    """
    data: List[Dict[str, Any]]
    row_count: int
    execution_time: float
    query: str
    success: bool
    error: Optional[str] = None


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class ConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    pass


class QueryError(DatabaseError):
    """Exception raised when query execution fails."""
    pass


class TransactionError(DatabaseError):
    """Exception raised when transaction operations fail."""
    pass


class MySQLConnectionBase(ABC):
    """
    Abstract base class for low-level MySQL connection/transaction managers.
    
    This is internal to the MySQL adapter layer; domain-specific managers
    should instead extend `Database.managers.base.BaseDatabaseManager`,
    which wraps this adapter and injects the appropriate database name.
    """
    
    def __init__(self, config: DatabaseConfig):
        """Initialize the database manager with configuration."""
        self.config = config
        self._lock = threading.RLock()
        self._connection_pools: Dict[str, Any] = {}
        self._is_initialized = False
        
    @abstractmethod
    def _create_connection_pool(self, database_name: str) -> Any:
        """Create a connection pool for the specified database."""
        pass
    
    @abstractmethod
    def _get_connection(self, database_name: str) -> Any:
        """Get a connection from the pool."""
        pass
    
    @abstractmethod
    def _close_connection(self, connection: Any) -> None:
        """Close a connection and return it to the pool."""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Tuple] = None, 
                     database: str = None, fetch: bool = True) -> QueryResult:
        """Execute a query and return results."""
        pass
    
    @abstractmethod
    def execute_many(self, query: str, params_list: List[Tuple], 
                    database: str = None) -> QueryResult:
        """Execute a query multiple times with different parameters."""
        pass
    
    @abstractmethod
    def begin_transaction(self, database: str = None) -> Any:
        """Begin a database transaction."""
        pass
    
    @abstractmethod
    def commit_transaction(self, transaction: Any) -> None:
        """Commit a database transaction."""
        pass
    
    @abstractmethod
    def rollback_transaction(self, transaction: Any) -> None:
        """Rollback a database transaction."""
        pass
    
    @contextmanager
    def transaction(self, database: str = None) -> Iterator[Any]:
        """Context manager for database transactions."""
        transaction = None
        try:
            transaction = self.begin_transaction(database)
            yield transaction
            self.commit_transaction(transaction)
        except Exception as e:
            if transaction:
                self.rollback_transaction(transaction)
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the database connection."""
        try:

            # timing to see how long it takes to connect to the database
            start_time = time.time()
            
            # try to connect to any available database
            available_dbs = list(self._connection_pools.keys())
            if not available_dbs:
                return {
                    'status': 'unhealthy',
                    'response_time': None,
                    'timestamp': datetime.now().isoformat(),
                    'error': 'No database connections available'
                }
            
            # use the first available database for health check
            test_db = available_dbs[0]
            result = self.execute_query("SELECT 1 as health_check", database=test_db, fetch=True)
            execution_time = time.time() - start_time
            
            # return the result of the health check
            return {
                'status': 'healthy' if result.success else 'unhealthy',
                'response_time': execution_time,
                'timestamp': datetime.now().isoformat(),
                'error': result.error,
                'tested_database': test_db
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'response_time': None,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about database connections."""
        return {
            'host': self.config.host,
            'port': self.config.port,
            'database': self.config.database,
            'target': self.config.target,
            'pool_size': self.config.pool_size,
            'max_connections': self.config.max_connections,
            'initialized': self._is_initialized
        }


class MySQLDatabaseManager(MySQLConnectionBase):
    """
    MySQL-specific database manager with connection pooling.
    
    Provides optimized MySQL operations including:
    - Connection pooling for multiple databases
    - Vectorized bulk operations
    - Transaction management
    - Error handling and retry logic
    
    Delegates to the centralized DatabaseManager for configuration and pools.
    """
    
    def __init__(self, config: DatabaseConfig = None):
        """
        Initialize MySQL database manager.
        
        Args:
            config: Optional configuration override. By default, configuration
                    is loaded from the centralized DatabaseManager singleton.
        """
        # Get the centralized database manager
        from .config import DatabaseManager as CentralizedDM
        self._central_manager = CentralizedDM.get_instance()
        
        # Use the centralized config
        if config is None:
            config = self._central_manager.get_config()
        
        super().__init__(config)
        # Don't initialize pools here - use the centralized ones
        self._connection_pools = self._central_manager.pools
        self._is_initialized = True
    
    def _initialize_connection_pools(self) -> None:
        """Compatibility shim - pools are managed by centralized DatabaseManager."""
        # Pools are initialized and managed by the centralized DatabaseManager.
        # This method exists only to satisfy the abstract interface.
        return
    
    def _create_connection_pool(self, database_name: str) -> pooling.MySQLConnectionPool:
        """Return connection pool for the given database from the centralized manager."""
        return self._central_manager.pools.get(database_name)
    
    def _get_connection(self, database_name: str = None) -> mysql.connector.connection.MySQLConnection:
        """Get a connection from the appropriate pool."""
        # Delegate to centralized manager
        return self._central_manager.get_connection(database_name)
    
    def _close_connection(self, connection: mysql.connector.connection.MySQLConnection) -> None:
        """Close a connection and return it to the pool."""
        try:
            if connection.is_connected():
                connection.close()
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")
    
    def execute_query(self, query: str, params: Optional[Tuple] = None, 
                     database: str = None, fetch: bool = True) -> QueryResult:
        """Execute a query and return results."""
        start_time = time.time()
        connection = None
        cursor = None
        
        try:
            connection = self._get_connection(database)
            cursor = connection.cursor(dictionary=True)
            
            # Execute query
            cursor.execute(query, params or ())
            
            # Fetch results if requested
            data = []
            if fetch:
                data = cursor.fetchall()
            
            execution_time = time.time() - start_time
            
            return QueryResult(
                data=data,
                row_count=cursor.rowcount,
                execution_time=execution_time,
                query=query,
                success=True
            )
            
        except MySQLError as e:
            execution_time = time.time() - start_time
            error_str = str(e)
            
            # Filter out "Table already exists" errors as they're expected with IF NOT EXISTS
            if "1050" in error_str and "already exists" in error_str:
                # This is expected behavior for CREATE TABLE IF NOT EXISTS
                logger.debug(f"Table already exists (expected): {e}")
                return QueryResult(
                    data=[],
                    row_count=0,
                    execution_time=execution_time,
                    query=query,
                    success=True  # This is actually success for IF NOT EXISTS
                )
            else:
                logger.error(f"Query execution failed: {e}")
                return QueryResult(
                    data=[],
                    row_count=0,
                    execution_time=execution_time,
                    query=query,
                    success=False,
                    error=error_str
                )
        finally:
            if cursor:
                cursor.close()
            if connection:
                self._close_connection(connection)
    
    def execute_many(self, query: str, params_list: List[Tuple], 
                    database: str = None) -> QueryResult:
        """Execute a query multiple times with different parameters using adaptive batch sizing."""
        start_time = time.time()
        connection = None
        cursor = None
        
        # Fast-path: nothing to do
        if not params_list:
            return QueryResult(
                data=[],
                row_count=0,
                execution_time=0.0,
                query=query,
                success=True
            )

        try:
            connection = self._get_connection(database)
            cursor = connection.cursor()
            
            # Determine initial batch size from environment (default 50000)
            try:
                env_batch = int(os.getenv('DB_INSERT_BATCH_SIZE', '50000'))
            except Exception:
                env_batch = 50000
            batch_size = max(1, min(env_batch, len(params_list)))
            # Lower threshold for wide tables - estimate based on first row size
            # If params_list has values, estimate columns from first tuple length
            if params_list:
                estimated_columns = len(params_list[0])
                # For wide tables (100+ columns), lower threshold significantly
                if estimated_columns > 100:
                    min_batch_threshold = max(100, 5000 // (estimated_columns // 50))
                elif estimated_columns > 50:
                    min_batch_threshold = max(500, 10000 // (estimated_columns // 25))
                else:
                    min_batch_threshold = 10000  # Standard threshold for narrow tables
            else:
                min_batch_threshold = 10000

            total_row_count = 0
            i = 0
            last_error: Optional[str] = None

            while i < len(params_list):
                current_batch_size = min(batch_size, len(params_list) - i)
                current_params = params_list[i:i + current_batch_size]

                try:
                    cursor.executemany(query, current_params)
                    total_row_count += cursor.rowcount
                    i += current_batch_size
                    last_error = None
                except MySQLError as e:
                    error_str = str(e)
                    lower_err = error_str.lower()
                    # Handle max_allowed_packet packet too big (error 1153)
                    if 'max_allowed_packet' in lower_err or '1153' in lower_err:
                        new_batch_size = batch_size // 2
                        logger.warning(
                            f"Bulk insert failed due to max_allowed_packet (batch_size={batch_size}). "
                            f"Retrying with batch_size={new_batch_size}"
                        )
                        if new_batch_size < min_batch_threshold:
                            msg = (
                                f"Adaptive batching failed: batch_size dropped below {min_batch_threshold} "
                                f"while inserting. Last error: {error_str}"
                            )
                            logger.error(msg)
                            execution_time = time.time() - start_time
                            return QueryResult(
                                data=[],
                                row_count=total_row_count,
                                execution_time=execution_time,
                                query=query,
                                success=False,
                                error=msg
                            )
                        batch_size = new_batch_size
                        last_error = error_str
                        # Retry same range with smaller batch_size
                        continue
                    # Lost connection/server gone away (2013/2006)
                    elif '2013' in lower_err or '2006' in lower_err or 'server has gone away' in lower_err or 'lost connection' in lower_err:
                        # Reduce batch size and refresh connection/cursor, then retry
                        new_batch_size = max(1, batch_size // 2)
                        logger.warning(
                            f"Bulk insert lost connection (batch_size={batch_size}). Retrying with batch_size={new_batch_size}"
                        )
                        if new_batch_size < min_batch_threshold:
                            msg = (
                                f"Adaptive batching failed due to lost connection: batch_size dropped below {min_batch_threshold}. "
                                f"Last error: {error_str}"
                            )
                            logger.error(msg)
                            execution_time = time.time() - start_time
                            return QueryResult(
                                data=[],
                                row_count=total_row_count,
                                execution_time=execution_time,
                                query=query,
                                success=False,
                                error=msg
                            )
                        # Close current cursor/connection and reopen
                        if cursor:
                            try:
                                cursor.close()
                            except Exception:
                                pass
                            cursor = None
                        if connection:
                            try:
                                connection.close()  # Force close, don't return to pool
                            except Exception:
                                pass
                            connection = None
                        # Small delay to let MySQL server and pool recover
                        time.sleep(0.5)
                        connection = self._get_connection(database)
                        cursor = connection.cursor()
                        batch_size = new_batch_size
                        last_error = error_str
                        continue
                    else:
                        # Non-adaptive error: abort
                        logger.error(f"Bulk query execution failed: {e}")
                        execution_time = time.time() - start_time
                        return QueryResult(
                            data=[],
                            row_count=total_row_count,
                            execution_time=execution_time,
                            query=query,
                            success=False,
                            error=error_str
                        )
            
            execution_time = time.time() - start_time
            return QueryResult(
                data=[],
                row_count=total_row_count,
                execution_time=execution_time,
                query=query,
                success=True
                )
        finally:
            if cursor:
                cursor.close()
            if connection:
                self._close_connection(connection)
    
    def begin_transaction(self, database: str = None) -> mysql.connector.connection.MySQLConnection:
        """Begin a database transaction."""
        connection = self._get_connection(database)
        connection.start_transaction()
        return connection
    
    def commit_transaction(self, transaction: mysql.connector.connection.MySQLConnection) -> None:
        """Commit a database transaction."""
        try:
            transaction.commit()
        finally:
            self._close_connection(transaction)
    
    def rollback_transaction(self, transaction: mysql.connector.connection.MySQLConnection) -> None:
        """Rollback a database transaction."""
        try:
            transaction.rollback()
        finally:
            self._close_connection(transaction)
    
    def vectorized_insert(self, table: str, data: List[Dict[str, Any]], 
                         database: str = None, batch_size: int = 1000) -> QueryResult:
        """
        Perform vectorized bulk insert operations.
        
        Args:
            table: Target table name
            data: List of dictionaries containing row data
            database: Target database name
            batch_size: Number of rows to insert per batch
            
        Returns:
            QueryResult with operation details
        """
        if not data:
            return QueryResult(
                data=[],
                row_count=0,
                execution_time=0.0,
                query="vectorized_insert",
                success=True
            )
        
        start_time = time.time()
        total_rows = 0
        
        try:
            # Get column names from first row
            columns = list(data[0].keys())
            placeholders = ', '.join(['%s'] * len(columns))
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            
            # Process data in batches
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                batch_params = [tuple(row[col] for col in columns) for row in batch]
                
                result = self.execute_many(query, batch_params, database)
                if not result.success:
                    raise QueryError(f"Batch insert failed: {result.error}")
                
                total_rows += result.row_count
            
            execution_time = time.time() - start_time
            
            return QueryResult(
                data=[],
                row_count=total_rows,
                execution_time=execution_time,
                query=f"vectorized_insert_{table}",
                success=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Vectorized insert failed: {e}")
            return QueryResult(
                data=[],
                row_count=total_rows,
                execution_time=execution_time,
                query=f"vectorized_insert_{table}",
                success=False,
                error=str(e)
            )
    
    def vectorized_update(self, table: str, data: List[Dict[str, Any]], 
                         where_columns: List[str], database: str = None,
                         batch_size: int = 1000) -> QueryResult:
        """
        Perform vectorized bulk update operations.
        
        Args:
            table: Target table name
            data: List of dictionaries containing row data
            where_columns: Columns to use in WHERE clause
            database: Target database name
            batch_size: Number of rows to update per batch
            
        Returns:
            QueryResult with operation details
        """
        if not data:
            return QueryResult(
                data=[],
                row_count=0,
                execution_time=0.0,
                query="vectorized_update",
                success=True
            )
        
        start_time = time.time()
        total_rows = 0
        
        try:
            # Get all columns
            all_columns = list(data[0].keys())
            update_columns = [col for col in all_columns if col not in where_columns]
            
            if not update_columns:
                raise ValueError("No columns to update (all columns are in WHERE clause)")
            
            # Build UPDATE query
            set_clause = ', '.join([f"{col} = %s" for col in update_columns])
            where_clause = ' AND '.join([f"{col} = %s" for col in where_columns])
            query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
            
            # Process data in batches
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                batch_params = []
                
                for row in batch:
                    # Order: update columns first, then where columns
                    params = tuple(row[col] for col in update_columns) + tuple(row[col] for col in where_columns)
                    batch_params.append(params)
                
                result = self.execute_many(query, batch_params, database)
                if not result.success:
                    raise QueryError(f"Batch update failed: {result.error}")
                
                total_rows += result.row_count
            
            execution_time = time.time() - start_time
            
            return QueryResult(
                data=[],
                row_count=total_rows,
                execution_time=execution_time,
                query=f"vectorized_update_{table}",
                success=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Vectorized update failed: {e}")
            return QueryResult(
                data=[],
                row_count=total_rows,
                execution_time=execution_time,
                query=f"vectorized_update_{table}",
                success=False,
                error=str(e)
            )
    
    def vectorized_upsert(self, table: str, data: List[Dict[str, Any]], 
                         conflict_columns: List[str], database: str = None,
                         batch_size: int = 1000) -> QueryResult:
        """
        Perform vectorized bulk upsert operations (INSERT ... ON DUPLICATE KEY UPDATE).
        
        Args:
            table: Target table name
            data: List of dictionaries containing row data
            conflict_columns: Columns that define conflicts for upsert
            database: Target database name
            batch_size: Number of rows to upsert per batch
            
        Returns:
            QueryResult with operation details
        """
        if not data:
            return QueryResult(
                data=[],
                row_count=0,
                execution_time=0.0,
                query="vectorized_upsert",
                success=True
            )
        
        start_time = time.time()
        total_rows = 0
        
        try:
            # Get all columns
            all_columns = list(data[0].keys())
            update_columns = [col for col in all_columns if col not in conflict_columns]
            
            # Build UPSERT query
            columns_str = ', '.join(all_columns)
            placeholders = ', '.join(['%s'] * len(all_columns))
            update_clause = ', '.join([f"{col} = VALUES({col})" for col in update_columns])
            
            query = f"""
                INSERT INTO {table} ({columns_str}) 
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE {update_clause}
            """
            
            # Process data in batches
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                batch_params = [tuple(row[col] for col in all_columns) for row in batch]
                
                result = self.execute_many(query, batch_params, database)
                if not result.success:
                    # Diagnose first failing row by attempting single-row upserts
                    try:
                        for idx, row in enumerate(batch):
                            try:
                                single_params = tuple(row[col] for col in all_columns)
                                single_res = self.execute_query(query, single_params, database, fetch=False)
                                if not single_res.success:
                                    raise QueryError(single_res.error)
                            except Exception as single_err:
                                logger.error(
                                    f"Upsert diagnostic: first failing row in batch for table {table} at global_index={i+idx}: {single_err}"
                                )
                                # Print a concise snapshot of the row to aid debugging
                                try:
                                    snapshot_items = []
                                    for k in all_columns:
                                        v = row.get(k)
                                        # shorten long values
                                        if isinstance(v, str) and len(v) > 200:
                                            v_disp = v[:200] + "..."
                                        else:
                                            v_disp = v
                                        snapshot_items.append(f"{k}={v_disp}")
                                    snapshot = ", ".join(snapshot_items[:20])
                                    logger.error(f"Failing row snapshot: {snapshot}")
                                except Exception:
                                    logger.error("Could not render failing row snapshot")
                                break
                    except Exception as diag_err:
                        logger.error(f"Upsert diagnostic failed: {diag_err}")
                    raise QueryError(f"Batch upsert failed: {result.error}")
                
                total_rows += result.row_count
            
            execution_time = time.time() - start_time
            
            return QueryResult(
                data=[],
                row_count=total_rows,
                execution_time=execution_time,
                query=f"vectorized_upsert_{table}",
                success=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Vectorized upsert failed: {e}")
            return QueryResult(
                data=[],
                row_count=total_rows,
                execution_time=execution_time,
                query=f"vectorized_upsert_{table}",
                success=False,
                error=str(e)
            )


def execute_query(query: str, params: Optional[Tuple] = None, 
                 database: str = None, fetch: bool = True) -> QueryResult:
    """Execute a query using the global database manager."""
    manager = MySQLDatabaseManager()
    return manager.execute_query(query, params, database, fetch)


def execute_many(query: str, params_list: List[Tuple], database: str = None) -> QueryResult:
    """Execute a query multiple times using the global database manager."""
    manager = MySQLDatabaseManager()
    return manager.execute_many(query, params_list, database)


def vectorized_insert(table: str, data: List[Dict[str, Any]], 
                     database: str = None, batch_size: int = 1000) -> QueryResult:
    """Perform vectorized bulk insert using the global database manager."""
    manager = MySQLDatabaseManager()
    return manager.vectorized_insert(table, data, database, batch_size)


def vectorized_update(table: str, data: List[Dict[str, Any]], 
                     where_columns: List[str], database: str = None,
                     batch_size: int = 1000) -> QueryResult:
    """Perform vectorized bulk update using the global database manager."""
    manager = MySQLDatabaseManager()
    return manager.vectorized_update(table, data, where_columns, database, batch_size)


def vectorized_upsert(table: str, data: List[Dict[str, Any]], 
                     conflict_columns: List[str], database: str = None,
                     batch_size: int = 1000) -> QueryResult:
    """Perform vectorized bulk upsert using the global database manager."""
    manager = MySQLDatabaseManager()
    return manager.vectorized_upsert(table, data, conflict_columns, database, batch_size)


@contextmanager
def transaction(database: str = None):
    """Context manager for database transactions using the global database manager."""
    manager = MySQLDatabaseManager()
    with manager.transaction(database) as txn:
        yield txn

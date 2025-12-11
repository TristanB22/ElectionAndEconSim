#!/usr/bin/env python3
"""
L2 Data Manager for World_Sim

Specialized database manager for L2 voter data operations.
Handles bulk loading, vectorized operations, and efficient data processing.
"""

import os
import sys
import time
import logging
import threading
from typing import Dict, List, Any, Optional, Tuple, Iterator
from pathlib import Path
from contextlib import contextmanager
import pandas as pd
import numpy as np
import json

from Utils.path_manager import initialize_paths
initialize_paths()

from Database.database_manager import (
    MySQLDatabaseManager, DatabaseConfig, QueryResult, 
    vectorized_insert, vectorized_upsert
)

logger = logging.getLogger(__name__)


class L2DataManager:
    """
    Specialized manager for L2 voter data operations.
    
    Provides optimized operations for:
    - Bulk L2 data loading
    - Vectorized database operations
    - Memory-efficient data processing
    - Integration with existing L2 data system
    """
    
    def __init__(self, db_manager: MySQLDatabaseManager = None):
        """Initialize L2 data manager."""
        self.db_manager = db_manager or MySQLDatabaseManager()
        self.agents_db = os.getenv('DB_AGENTS_NAME', 'world_sim_agents')
        
    def load_l2_data_bulk(self, data: List[Dict[str, Any]], 
                          batch_size: int = 10000, 
                          table_mapping: Dict[str, List[str]] = None) -> Dict[str, QueryResult]:
        """
        Load L2 data in bulk across multiple tables.
        
        Args:
            data: List of L2 data records
            batch_size: Number of records per batch
            table_mapping: Mapping of table names to column lists
            
        Returns:
            Dictionary mapping table names to QueryResult objects
        """
        if not data:
            return {}
        
        results = {}
        
        # Default table mapping if not provided
        if not table_mapping:
            table_mapping = self._get_default_table_mapping()
        
        # Process each table
        for table_name, columns in table_mapping.items():
            try:
                # Extract relevant data for this table - this now ensures ALL records get rows
                table_data = self._extract_table_data(data, columns)
                
                # Always process the table data, even if some fields are NULL
                if not table_data:
                    logger.warning(f"No data extracted for {table_name} - this should not happen with the new logic")
                    continue
                
                # Perform vectorized insert
                result = vectorized_upsert(
                    table=table_name,
                    data=table_data,
                    conflict_columns=['LALVOTERID'],
                    database=self.agents_db,
                    batch_size=batch_size
                )
                
                results[table_name] = result
                
                if result.success:
                    logger.info(f"Loaded {result.row_count} rows into {table_name}")
                else:
                    logger.error(f"Failed to load data into {table_name}: {result.error}")
                    
            except Exception as e:
                logger.error(f"Error loading data into {table_name}: {e}")
                results[table_name] = QueryResult(
                    data=[],
                    row_count=0,
                    execution_time=0.0,
                    query=f"load_l2_data_bulk_{table_name}",
                    success=False,
                    error=str(e)
                )
        
        return results
    
    def _get_default_table_mapping(self) -> Dict[str, List[str]]:
        """Get default table mapping for L2 data.
        Tries to load the full mapping from Setup/Database/schemas/l2_column_mapping.json.
        Falls back to a minimal mapping if the file is unavailable.
        """
        try:
            # Locate mapping JSON relative to project root
            project_root = Path(__file__).resolve().parents[1]
            mapping_path = project_root / 'Setup' / 'Database' / 'schemas' / 'l2_column_mapping.json'
            if mapping_path.exists():
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)

                buckets: Dict[str, List[str]] = mapping.get('buckets', {})
                safe_map: Dict[str, str] = mapping.get('safe_column_mapping', {})

                # Helper to map raw column names to DB-safe names
                def to_db(col_list: List[str]) -> List[str]:
                    return ['LALVOTERID'] + [safe_map[c] for c in col_list if c in safe_map]

                full_mapping: Dict[str, List[str]] = {}

                # Core tables
                if 'agent_core' in buckets and buckets['agent_core']:
                    full_mapping['l2_agent_core'] = to_db(buckets['agent_core'])

                if 'location' in buckets and buckets['location']:
                    # Keep LALVOTERID first; remove duplicates
                    cols = to_db(buckets['location'])
                    seen = set()
                    dedup_cols: List[str] = []
                    for c in cols:
                        if c not in seen:
                            seen.add(c)
                            dedup_cols.append(c)
                    full_mapping['l2_location'] = dedup_cols

                # Political split into parts of 120 columns
                if 'political' in buckets and buckets['political']:
                    pol_cols = [safe_map[c] for c in buckets['political'] if c in safe_map]
                    chunk_size = 120
                    chunks = [pol_cols[i:i + chunk_size] for i in range(0, len(pol_cols), chunk_size)]
                    for idx, chunk in enumerate(chunks, start=1):
                        full_mapping[f'l2_political_part_{idx}'] = ['LALVOTERID'] + chunk

                # Other split into parts of 120 columns
                if 'other' in buckets and buckets['other']:
                    other_cols = [safe_map[c] for c in buckets['other'] if c in safe_map]
                    chunk_size = 120
                    chunks = [other_cols[i:i + chunk_size] for i in range(0, len(other_cols), chunk_size)]
                    for idx, chunk in enumerate(chunks, start=1):
                        full_mapping[f'l2_other_part_{idx}'] = ['LALVOTERID'] + chunk

                # Geo table always explicit
                full_mapping['l2_geo'] = ['LALVOTERID', 'latitude', 'longitude']

                # Ensure we have at least the three base tables
                if not full_mapping:
                    raise ValueError('Empty mapping built from JSON')
                return full_mapping

        except Exception as e:
            logger.warning(f"Falling back to minimal default L2 table mapping: {e}")

        # Fallback minimal mapping
        return {
            'l2_agent_core': [
                'LALVOTERID', 'SEQUENCE', 'Voters_FirstName', 'Voters_LastName',
                'Voters_MiddleName', 'Voters_NameSuffix', 'Voters_Age', 'Voters_Gender',
                'Voters_BirthDate', 'Voters_StateVoterID', 'Voters_CountyVoterID'
            ],
            'l2_location': [
                'LALVOTERID', 'Residence_Addresses_AddressLine', 'Residence_Addresses_ExtraAddressLine',
                'Residence_Addresses_City', 'Residence_Addresses_State', 'Residence_Addresses_Zip',
                'Residence_Addresses_ZipPlus4', 'Residence_Addresses_DPBC', 'Residence_Addresses_CheckDigit',
                'Residence_Addresses_HouseNumber', 'Residence_Addresses_PrefixDirection', 'Residence_Addresses_StreetName',
                'Residence_Addresses_Designator', 'Residence_Addresses_SuffixDirection', 'Residence_Addresses_ApartmentNum',
                'Residence_Addresses_ApartmentType', 'Residence_Addresses_CassErrStatCode', 'Residence_Addresses_CensusTract',
                'Residence_Addresses_CensusBlockGroup', 'Residence_Addresses_CensusBlock', 'Residence_Addresses_Complete_Census_Geocode',
                'Residence_Addresses_LatLongAccuracy', 'Residence_Addresses_Property_Land_Square_Footage', 'Residence_Addresses_Property_Type',
                'Mailing_Addresses_AddressLine', 'Mailing_Addresses_ExtraAddressLine', 'Mailing_Addresses_City',
                'Mailing_Addresses_State', 'Mailing_Addresses_Zip', 'Mailing_Addresses_ZipPlus4',
                'Mailing_Addresses_DPBC', 'Mailing_Addresses_CheckDigit', 'Mailing_Addresses_HouseNumber',
                'Mailing_Addresses_PrefixDirection', 'Mailing_Addresses_StreetName', 'Mailing_Addresses_Designator',
                'Mailing_Addresses_SuffixDirection', 'Mailing_Addresses_ApartmentNum', 'Mailing_Addresses_ApartmentType',
                'Mailing_Addresses_CassErrStatCode', 'County', 'City', 'Residence_Addresses_Density',
                'Residence_Addresses_Property_Home_Square_Footage'
            ],
            'l2_geo': ['LALVOTERID', 'latitude', 'longitude']
        }
    
    def _extract_table_data(self, data: List[Dict[str, Any]], 
                           columns: List[str]) -> List[Dict[str, Any]]:
        """Extract data for specific table columns. Ensures ALL records get a row in every table."""
        table_data = []
        
        # Column mapping from L2 data names to database names
        column_mapping = {
            'Residence_Addresses_Latitude': 'latitude',
            'Residence_Addresses_Longitude': 'longitude'
        }
        
        # Process EVERY record to ensure all agents get rows in all tables
        for record in data:
            # Skip records without LALVOTERID
            if 'LALVOTERID' not in record or not record['LALVOTERID']:
                continue
                
            table_record = {'LALVOTERID': record['LALVOTERID']}  # Always include LALVOTERID
            
            # Process each column for this table
            for col in columns:
                if col == 'LALVOTERID':
                    continue  # Already handled above
                    
                # Check if we need to map the column name
                source_col = col
                for l2_name, db_name in column_mapping.items():
                    if col == db_name and l2_name in record:
                        source_col = l2_name
                        break
                
                # Always include the column, even if the source data is missing
                if source_col in record and record[source_col] is not None:
                    # Clean the value based on column type
                    value = record[source_col]
                    if col in ['latitude', 'longitude']:
                        # Special handling for geographic coordinates
                        try:
                            table_record[col] = float(value) if value and not pd.isna(value) else None
                        except (ValueError, TypeError):
                            table_record[col] = None
                    else:
                        table_record[col] = value
                else:
                    table_record[col] = None
            
            table_data.append(table_record)
        
        return table_data
    
    def process_l2_dataframe(self, df: pd.DataFrame, 
                            table_mapping: Dict[str, List[str]] = None) -> Dict[str, QueryResult]:
        """
        Process a pandas DataFrame containing L2 data.
        
        Args:
            df: Pandas DataFrame with L2 data
            table_mapping: Mapping of table names to column lists
            
        Returns:
            Dictionary mapping table names to QueryResult objects
        """
        # Convert DataFrame to list of dictionaries
        data = df.to_dict('records')
        
        # Clean data
        data = self._clean_l2_data(data)
        
        return self.load_l2_data_bulk(data, table_mapping=table_mapping)
    
    def _clean_l2_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean L2 data for database insertion."""
        cleaned_data = []
        
        # Column length limits based on database schema
        column_limits = {
            'Residence_Addresses_LatLongAccuracy': 10,
            'Residence_Addresses_AddressLine': 500,
            'Residence_Addresses_ExtraAddressLine': 500,
            'Residence_Addresses_City': 255,
            'Residence_Addresses_State': 2,
            'Mailing_Addresses_AddressLine': 500,
            'Mailing_Addresses_ExtraAddressLine': 500,
            'Mailing_Addresses_City': 255,
            'Mailing_Addresses_State': 2,
            'Residence_Addresses_StreetName': 255,
            'Mailing_Addresses_StreetName': 255,
            'Residence_Addresses_PrefixDirection': 10,
            'Residence_Addresses_SuffixDirection': 10,
            'Mailing_Addresses_PrefixDirection': 10,
            'Mailing_Addresses_SuffixDirection': 10,
            'Residence_Addresses_Designator': 20,
            'Mailing_Addresses_Designator': 20,
            'Residence_Addresses_ApartmentNum': 20,
            'Residence_Addresses_ApartmentType': 20,
            'Mailing_Addresses_ApartmentNum': 20,
            'Mailing_Addresses_ApartmentType': 20,
            'Residence_Addresses_CassErrStatCode': 10,
            'Mailing_Addresses_CassErrStatCode': 10,
            'Residence_Addresses_Complete_Census_Geocode': 20,
            'Residence_Addresses_Property_Type': 50,
            'County': 255,
            'City': 255,
            'Residence_Addresses_Density': 20,
            'Residence_Addresses_HouseNumber': 20,
            'Mailing_Addresses_HouseNumber': 20
        }
        
        for record in data:
            cleaned_record = {}
            
            for key, value in record.items():
                # Handle NaN values
                if pd.isna(value):
                    cleaned_record[key] = None
                # Handle date fields
                elif key in ['Voters_BirthDate', 'Voters_CalculatedRegDate', 
                           'Voters_OfficialRegDate', 'Voters_MovedFrom_Date']:
                    cleaned_record[key] = self._convert_date_field(value)
                # Handle boolean-like fields (election flags and donor political flags)
                elif self._is_boolean_field(key):
                    cleaned_record[key] = self._coerce_bool(value)
                # Handle numeric fields
                elif key in ['Residence_Addresses_Latitude', 'Residence_Addresses_Longitude']:
                    cleaned_record[key] = self._convert_numeric_field(value)
                # Handle all other fields
                else:
                    if value is not None:
                        str_value = str(value).strip()
                        # Truncate if column has length limit
                        if key in column_limits:
                            max_length = column_limits[key]
                            if len(str_value) > max_length:
                                str_value = str_value[:max_length]
                        cleaned_record[key] = str_value
                    else:
                        cleaned_record[key] = None
            
            cleaned_data.append(cleaned_record)
        
        return cleaned_data

    def _is_boolean_field(self, source_column_name: str) -> bool:
        """Return True if the given source column should be treated as boolean.
        Includes election flags and consumer donor political flags.
        """
        try:
            name = str(source_column_name)
        except Exception:
            return False

        upper_name = name.upper()
        if upper_name in {"CONSUMERDATA_DONOR_POLITICAL_CONSERVATIVE", "CONSUMERDATA_DONOR_POLITICAL_LIBERAL", "CONSUMERDATA_HOUSE_PLANTS"}:
            return True

        import re
        if re.match(r"^(ANYELECTION|GENERAL|PRIMARY|OTHERELECTION|PRESIDENTIALPRIMARY)_\d{4}$", upper_name):
            return True
        # Treat any column explicitly marked as a flag as boolean
        return upper_name.endswith("_FLAG")

    def _coerce_bool(self, value: Any) -> Optional[int]:
        """Map Y/N-like inputs to 1/0/NULL for BOOLEAN/TINYINT columns."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, (int, bool)):
            return int(bool(value))
        s = str(value).strip().upper()
        if s in {"Y", "YES", "TRUE", "T", "1"}:
            return 1
        if s in {"N", "NO", "FALSE", "F", "0"}:
            return 0
        return None
    
    def _convert_date_field(self, value: Any) -> Optional[str]:
        """Convert date field to MySQL format."""
        if pd.isna(value) or value is None:
            return None
        
        try:
            if isinstance(value, str) and '/' in str(value):
                from datetime import datetime
                date_obj = datetime.strptime(str(value), '%m/%d/%Y')
                return date_obj.strftime('%Y-%m-%d')
            return str(value)
        except (ValueError, TypeError):
            return None
    
    def _convert_numeric_field(self, value: Any) -> Optional[float]:
        """Convert numeric field to float."""
        if pd.isna(value) or value is None:
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def get_l2_data_by_voter_id(self, voter_id: str, 
                               tables: List[str] = None) -> Dict[str, Any]:
        """
        Get complete L2 data for a voter by LALVOTERID.
        
        Args:
            voter_id: LALVOTERID to search for
            tables: List of tables to query (default: all L2 tables)
            
        Returns:
            Dictionary containing all L2 data for the voter
        """
        if not tables:
            tables = ['l2_agent_core', 'l2_location', 'l2_geo', 
                     'l2_political_part_1', 'l2_political_part_2', 'l2_political_part_3',
                     'l2_other_part_1', 'l2_other_part_2', 'l2_other_part_3', 'l2_other_part_4']
        
        voter_data = {}
        
        for table in tables:
            try:
                query = f"SELECT * FROM {table} WHERE LALVOTERID = %s"
                result = self.db_manager.execute_query(
                    query, (voter_id,), database=self.agents_db, fetch=True
                )
                
                if result.success and result.data:
                    voter_data[table] = result.data[0]
                else:
                    voter_data[table] = None
                    
            except Exception as e:
                logger.error(f"Error querying {table} for voter {voter_id}: {e}")
                voter_data[table] = None
        
        return voter_data
    
    def search_l2_data(self, criteria: Dict[str, Any], 
                      tables: List[str] = None, 
                      limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search L2 data based on criteria.
        
        Args:
            criteria: Dictionary of search criteria
            tables: List of tables to search (default: l2_agent_core)
            limit: Maximum number of results
            
        Returns:
            List of matching records
        """
        if not tables:
            tables = ['l2_agent_core']
        
        # Build WHERE clause
        where_conditions = []
        params = []
        
        for key, value in criteria.items():
            if value is not None:
                where_conditions.append(f"{key} = %s")
                params.append(value)
        
        if not where_conditions:
            return []
        
        where_clause = " AND ".join(where_conditions)
        
        # Query each table
        all_results = []
        
        for table in tables:
            try:
                query = f"SELECT * FROM {table} WHERE {where_clause} LIMIT %s"
                result = self.db_manager.execute_query(
                    query, tuple(params + [limit]), database=self.agents_db, fetch=True
                )
                
                if result.success:
                    all_results.extend(result.data)
                    
            except Exception as e:
                logger.error(f"Error searching {table}: {e}")
        
        return all_results
    
    def get_l2_statistics(self) -> Dict[str, Any]:
        """Get statistics about L2 data in the database."""
        stats = {}
        
        tables = ['l2_agent_core', 'l2_location', 'l2_geo', 
                 'l2_political_part_1', 'l2_political_part_2', 'l2_political_part_3',
                 'l2_other_part_1', 'l2_other_part_2', 'l2_other_part_3', 'l2_other_part_4']
        
        for table in tables:
            try:
                query = f"SELECT COUNT(*) as count FROM {table}"
                result = self.db_manager.execute_query(
                    query, database=self.agents_db, fetch=True
                )
                
                if result.success and result.data:
                    stats[table] = result.data[0]['count']
                else:
                    stats[table] = 0
                    
            except Exception as e:
                logger.error(f"Error getting statistics for {table}: {e}")
                stats[table] = 0
        
        return stats
    
    def optimize_l2_tables(self) -> Dict[str, QueryResult]:
        """Optimize L2 tables for better performance."""
        results = {}
        
        tables = ['l2_agent_core', 'l2_location', 'l2_geo', 
                 'l2_political_part_1', 'l2_political_part_2', 'l2_political_part_3',
                 'l2_other_part_1', 'l2_other_part_2', 'l2_other_part_3', 'l2_other_part_4']
        
        for table in tables:
            try:
                # Analyze table
                analyze_query = f"ANALYZE TABLE {table}"
                analyze_result = self.db_manager.execute_query(
                    analyze_query, database=self.agents_db, fetch=False
                )
                
                # Optimize table
                optimize_query = f"OPTIMIZE TABLE {table}"
                optimize_result = self.db_manager.execute_query(
                    optimize_query, database=self.agents_db, fetch=False
                )
                
                results[table] = optimize_result
                
                if optimize_result.success:
                    logger.info(f"Optimized table {table}")
                else:
                    logger.error(f"Failed to optimize table {table}: {optimize_result.error}")
                    
            except Exception as e:
                logger.error(f"Error optimizing table {table}: {e}")
                results[table] = QueryResult(
                    data=[],
                    row_count=0,
                    execution_time=0.0,
                    query=f"optimize_{table}",
                    success=False,
                    error=str(e)
                )
        
        return results


# Global L2 data manager instance
_l2_manager: Optional[L2DataManager] = None
_l2_manager_lock = threading.Lock()


def get_l2_data_manager() -> L2DataManager:
    """Get the global L2 data manager instance (singleton pattern)."""
    global _l2_manager
    
    with _l2_manager_lock:
        if _l2_manager is None:
            _l2_manager = L2DataManager()
        return _l2_manager


def reset_l2_data_manager() -> None:
    """Reset the global L2 data manager (useful for testing)."""
    global _l2_manager
    
    with _l2_manager_lock:
        _l2_manager = None


# Convenience functions for L2 data operations
def load_l2_data_bulk(data: List[Dict[str, Any]], 
                      batch_size: int = 10000, 
                      table_mapping: Dict[str, List[str]] = None) -> Dict[str, QueryResult]:
    """Load L2 data in bulk using the global L2 data manager."""
    return get_l2_data_manager().load_l2_data_bulk(data, batch_size, table_mapping)


def process_l2_dataframe(df: pd.DataFrame, 
                        table_mapping: Dict[str, List[str]] = None) -> Dict[str, QueryResult]:
    """Process L2 DataFrame using the global L2 data manager."""
    return get_l2_data_manager().process_l2_dataframe(df, table_mapping)


def get_l2_data_by_voter_id(voter_id: str, 
                           tables: List[str] = None) -> Dict[str, Any]:
    """Get L2 data by voter ID using the global L2 data manager."""
    return get_l2_data_manager().get_l2_data_by_voter_id(voter_id, tables)


def search_l2_data(criteria: Dict[str, Any], 
                  tables: List[str] = None, 
                  limit: int = 100) -> List[Dict[str, Any]]:
    """Search L2 data using the global L2 data manager."""
    return get_l2_data_manager().search_l2_data(criteria, tables, limit)

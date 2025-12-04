#!/usr/bin/env python3
"""
L2 Data Loader for NAS Database

This script loads L2 voter data from .tab files into the NAS database.
It uses the existing column mapping system to properly distribute data across
the partitioned L2 tables.

Usage:
    python load_l2_data_to_nas.py --state AK --limit 100
    python load_l2_data_to_nas.py --state CA  # Load all data from CA
"""

import os
import sys
import argparse
import pandas as pd
import json
import glob
import mysql.connector
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from tqdm import tqdm
import multiprocessing as mp
from multiprocessing import Pool, Manager, Queue
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import create_engine

# Add the project root to the path for consistent imports FIRST
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now import project modules
from Utils.path_manager import initialize_paths
initialize_paths()

from Utils.environment_config import get_database_config

# Load environment variables using centralized loader
try:
    from Utils.env_loader import load_environment
    # Load from World_Sim root (parents[2])
    env_path = project_root / '.env'
    load_environment(env_path)
except ImportError:
    # Fallback to basic dotenv loading if centralized loader not available
    try:
        from dotenv import load_dotenv
        load_dotenv(project_root / '.env')
    except ImportError:
        print("Warning: python-dotenv not available. Environment variables may not be loaded.")

# Import database utilities
try:
    from Database.database_manager import MySQLDatabaseManager, vectorized_upsert
    from Database.l2_data_manager import get_l2_data_manager
    from Setup.Database.sql_executor import load_l2_column_mapping
except ImportError as e:
    print(f"Error importing database utilities: {e}")
    sys.exit(1)


class L2DataLoader:
    """Handles loading L2 data from files into the NAS database."""
    
    def __init__(self, debug: bool = False):
        """Initialize the L2 data loader."""
        self.l2_data_dir = os.getenv("L2_DATA_DIR")
        if not self.l2_data_dir:
            raise ValueError("L2_DATA_DIR environment variable not set")
        
        if not os.path.exists(self.l2_data_dir):
            raise ValueError(f"L2 data directory not found: {self.l2_data_dir}")
        
        self.column_mapping = None
        self.debug = debug
        self.db_manager = MySQLDatabaseManager()
        self.l2_manager = get_l2_data_manager()
    
    def _debug_print(self, message: str, start_time: float = None):
        """Print debug message with optional timing information."""
        if self.debug:
            if start_time is not None:
                elapsed = time.time() - start_time
                print(f"[DEBUG] {message} (took {elapsed:.2f}s)")
            else:
                print(f"[DEBUG] {message}")
    
    def _debug_timer(self, step_name: str):
        """Context manager for timing debug steps."""
        class DebugTimer:
            def __init__(self, loader, step_name):
                self.loader = loader
                self.step_name = step_name
                self.start_time = None
            
            def __enter__(self):
                if self.loader.debug:
                    self.start_time = time.time()
                    print(f"[DEBUG] Starting: {self.step_name}")
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.loader.debug and self.start_time is not None:
                    elapsed = time.time() - self.start_time
                    print(f"[DEBUG] Completed: {self.step_name} (took {elapsed:.2f}s)")
        
        return DebugTimer(self, step_name)
    
    def _get_file_size_bytes(self, file_path: str) -> int:
        """Get the file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            print(f"Error getting file size for {file_path}: {e}")
            return 0
    
    def _estimate_rows_per_file(self, file_path: str, sample_size: int = 100) -> int:
        """
        Estimate the number of rows in a file by sampling the first few rows
        and calculating average bytes per row.
        
        Args:
            file_path: Path to the file
            sample_size: Number of rows to sample for estimation
            
        Returns:
            Estimated number of rows in the file
        """
        try:
            file_size_bytes = self._get_file_size_bytes(file_path)
            if file_size_bytes == 0:
                return 0
            
            # Sample first few rows to estimate bytes per row
            with open(file_path, 'r', encoding='latin-1') as f:
                header_line = f.readline()  # Skip header
                header_size = len(header_line.encode('latin-1'))
                
                sample_bytes = 0
                sample_rows = 0
                
                for i, line in enumerate(f):
                    if i >= sample_size:
                        break
                    sample_bytes += len(line.encode('latin-1'))
                    sample_rows += 1
                
                if sample_rows == 0:
                    return 0
                
                # Calculate average bytes per row (excluding header)
                avg_bytes_per_row = sample_bytes / sample_rows
                
                # Estimate total rows: (file_size - header_size) / avg_bytes_per_row
                estimated_rows = int((file_size_bytes - header_size) / avg_bytes_per_row)
                
                if self.debug:
                    print(f"File {os.path.basename(file_path)}: {file_size_bytes:,} bytes, "
                          f"~{avg_bytes_per_row:.1f} bytes/row, estimated {estimated_rows:,} rows")
                
                return max(1, estimated_rows)  # At least 1 row
                
        except Exception as e:
            print(f"Error estimating rows for {file_path}: {e}")
            return 0
    
    def _get_database_config(self):
        """Get database configuration from the database manager."""
        return {
            'host': self.db_manager.config.host,
            'port': self.db_manager.config.port,
            'user': self.db_manager.config.user,
            'password': self.db_manager.config.password,
            'database': self.db_manager.config.database,
            'target': self.db_manager.config.target
        }
        
    def load_column_mapping(self):
        """Load the L2 column mapping configuration."""
        with self._debug_timer("Loading column mapping"):
            schema_dir = project_root / "Setup" / "Database" / "schemas"
            self.column_mapping = load_l2_column_mapping(schema_dir)
            
            if not self.column_mapping:
                raise ValueError("L2 column mapping not found")
            
            if not self.debug:
                print("Loaded L2 column mapping")
    
    def find_state_file(self, state: str) -> Optional[str]:
        """
        Find the L2 data file for the specified state.
        
        Args:
            state: Two-letter state code (e.g., 'AK', 'CA')
            
        Returns:
            Path to the state file or None if not found
        """
        with self._debug_timer(f"Finding file for state {state}"):
            # Look for files with the pattern: *VM2Uniform*{state}*.tab
            pattern = f"*VM2Uniform*{state.upper()}*.tab"
            
            import glob
            files = glob.glob(os.path.join(self.l2_data_dir, pattern))
            
            if not files:
                if not self.debug:
                    print(f"No L2 data file found for state: {state}")
                    print(f"   Searched pattern: {pattern}")
                    print(f"   In directory: {self.l2_data_dir}")
                return None
            
            if len(files) > 1 and not self.debug:
                print(f"Multiple files found for state {state}:")
                for f in files:
                    print(f"   - {os.path.basename(f)}")
                print(f"   Using: {os.path.basename(files[0])}")
            
            return files[0]
    
    def get_available_states(self) -> List[str]:
        """
        Get list of all available states based on files in the L2 data directory.
        
        Returns:
            List of two-letter state codes
        """
        if not self.l2_data_dir:
            return []
        
        # Look for all VM2Uniform files
        pattern = "*VM2Uniform*.tab"
        files = glob.glob(os.path.join(self.l2_data_dir, pattern))
        
        states = []
        for file_path in files:
            filename = os.path.basename(file_path)
            # Extract state code from filename like "VM2Uniform--AK.tab"
            if "VM2Uniform" in filename and filename.endswith(".tab"):
                # Try to extract state code from various patterns
                if "--" in filename:
                    # Pattern: VM2Uniform--AK.tab
                    state = filename.split("--")[-1].replace(".tab", "")
                elif "_" in filename:
                    # Pattern: VM2Uniform_AK.tab
                    state = filename.split("_")[-1].replace(".tab", "")
                else:
                    # Try to extract from other patterns
                    parts = filename.replace("VM2Uniform", "").replace(".tab", "").split("_")
                    if parts:
                        state = parts[-1]
                    else:
                        continue
                
                if len(state) == 2 and state.isalpha():
                    states.append(state.upper())
        
        return sorted(set(states))
    
    def _read_l2_file_standalone(self, file_path: str, limit: Optional[int] = None, debug: bool = False) -> pd.DataFrame:
        """
        Read L2 data file using standalone method without loader instance.
        
        Args:
            file_path: Path to the .tab file
            limit: Maximum number of rows to read (None for all)
            debug: Enable debug mode
            
        Returns:
            DataFrame with L2 data
        """
        if debug:
            print(f"Reading L2 data from: {os.path.basename(file_path)}")
        
        try:
            # Load complete header first
            column_names, column_order = self._load_complete_header_standalone(file_path)
            
            if not column_names:
                raise ValueError("Failed to load header from file")
            
            # Count total lines
            with open(file_path, 'rb') as f:
                total_lines = sum(1 for _ in f) - 1  # Subtract header row
            
            if limit:
                total_lines = min(total_lines, limit)
            
            if debug:
                print(f"Total lines to process: {total_lines:,}")
            
            # Read the entire file at once for simplicity in worker processes
            if total_lines <= 100000:  # Small files - read all at once
                df = pd.read_csv(
                    file_path,
                    sep='\t',
                    encoding='latin-1',
                    nrows=limit,
                    low_memory=False,
                    on_bad_lines='skip',
                    header=0
                )
            else:
                # Large files - read in chunks
                chunk_size = 50000
                all_data = []
                
                for start_line in range(0, total_lines, chunk_size):
                    end_line = min(start_line + chunk_size, total_lines)
                    
                    if start_line == 0:
                        # First chunk: include header row
                        df_chunk = pd.read_csv(
                            file_path,
                            sep='\t',
                            encoding='latin-1',
                            skiprows=0,
                            nrows=end_line - start_line + 1,  # +1 to include header
                            low_memory=False,
                            on_bad_lines='skip',
                            header=0  # Use header row
                        )
                    else:
                        # Subsequent chunks: skip header row and use complete column names
                        df_chunk = pd.read_csv(
                            file_path,
                            sep='\t',
                            encoding='latin-1',
                            skiprows=start_line + 1,  # +1 for header
                            nrows=end_line - start_line,
                            low_memory=False,
                            on_bad_lines='skip',
                            header=None  # No header row
                        )
                        # Set column names using the complete header we loaded
                        if column_names and len(column_names) >= len(df_chunk.columns):
                            df_chunk.columns = column_names[:len(df_chunk.columns)]
                        else:
                            # Fallback: pad with generic names if needed
                            if column_names:
                                df_chunk.columns = column_names[:len(df_chunk.columns)] + [f'col_{i}' for i in range(len(column_names), len(df_chunk.columns))]
                            else:
                                df_chunk.columns = [f'col_{i}' for i in range(len(df_chunk.columns))]
                    
                    # Clean data - handle NaN values properly
                    for col in df_chunk.columns:
                        df_chunk[col] = df_chunk[col].where(pd.notna(df_chunk[col]), None)
                    
                    all_data.append(df_chunk)
                
                # Combine all chunks
                df = pd.concat(all_data, ignore_index=True)
            
            # Apply limit if specified
            if limit and len(df) > limit:
                df = df.head(limit)
            
            if debug:
                print(f"Loaded {len(df):,} rows with {len(df.columns)} columns")
            
            return df
            
        except Exception as e:
            print(f"Error reading L2 file {file_path}: {e}")
            return pd.DataFrame()

    def _load_complete_header_standalone(self, file_path: str) -> Tuple[List[str], Dict[str, int]]:
        """
        Load the complete header row from the L2 file - standalone version.
        
        Args:
            file_path: Path to the L2 file
            
        Returns:
            Tuple of (column_names_list, column_name_to_position_dict)
        """
        try:
            # Read the header row to get ALL column names
            with open(file_path, 'r', encoding='latin-1') as f:
                header_line = f.readline().strip()
            
            # Split by tab to get ALL column names
            column_names = header_line.split('\t')
            
            # Create mapping from column names to positions for ALL columns
            column_mapping = {}
            for i, col_name in enumerate(column_names):
                column_mapping[col_name] = i
            
            return column_names, column_mapping
            
        except Exception as e:
            print(f"Error loading complete header: {e}")
            return [], {}

    def _load_complete_header(self, file_path: str) -> Tuple[List[str], Dict[str, int]]:
        """
        Load the complete header row from the L2 file and create a full column mapping.
        
        Args:
            file_path: Path to the L2 file
            
        Returns:
            Tuple of (column_names_list, column_name_to_position_dict)
        """
        try:
            # Read the header row to get ALL column names
            with open(file_path, 'r', encoding='latin-1') as f:
                header_line = f.readline().strip()
            
            # Split by tab to get ALL column names
            column_names = header_line.split('\t')
            
            print(f"Loaded complete header with {len(column_names)} columns")
            print(f"Header sample (first 10 columns): {column_names[:10]}")
            
            # Create mapping from column names to positions for ALL columns
            column_mapping = {}
            for i, col_name in enumerate(column_names):
                column_mapping[col_name] = i
            
            # Show some key columns we care about
            key_columns = ['SEQUENCE', 'LALVOTERID', 'Voters_FirstName', 'Voters_LastName', 
                          'Residence_Addresses_AddressLine', 'Residence_Addresses_City']
            detected_key_columns = {col: pos for col, pos in column_mapping.items() if col in key_columns}
            print(f"Key columns detected: {detected_key_columns}")
            
            return column_names, column_mapping
            
        except Exception as e:
            print(f"Error loading complete header: {e}")
            return [], {}

    def _process_chunk_standalone(self, chunk_info: Tuple[int, int, str, Optional[int], Dict[str, Any], List[str]], debug: bool = False) -> pd.DataFrame:
        """
        Process a single chunk of the file in parallel - standalone version without loader instance.
        
        Args:
            chunk_info: Tuple of (start_line, end_line, file_path, limit, column_mapping, column_names)
            
        Returns:
            DataFrame with processed chunk data
        """
        start_line, end_line, file_path, limit, column_mapping, column_names = chunk_info
        chunk_id = start_line // 50000 + 1
        
        try:
            if debug:
                print(f"Processing chunk {chunk_id}: lines {start_line}-{end_line}")
            
            # Read chunk with pandas - handle header row properly
            if start_line == 0:
                # First chunk: include header row
                df = pd.read_csv(
                    file_path,
                    sep='\t',
                    encoding='latin-1',
                    skiprows=0,
                    nrows=end_line - start_line + 1,  # +1 to include header
                    low_memory=False,
                    on_bad_lines='skip',
                    header=0  # Use header row
                )
            else:
                # Subsequent chunks: skip header row and use complete column names
                df = pd.read_csv(
                    file_path,
                    sep='\t',
                    encoding='latin-1',
                    skiprows=start_line + 1,  # +1 for header
                    nrows=end_line - start_line,
                    low_memory=False,
                    on_bad_lines='skip',
                    header=None  # No header row
                )
                # Set column names using the complete header we loaded
                if column_names and len(column_names) >= len(df.columns):
                    df.columns = column_names[:len(df.columns)]
                else:
                    # Fallback: pad with generic names if needed
                    if column_names:
                        df.columns = column_names[:len(df.columns)] + [f'col_{i}' for i in range(len(column_names), len(df.columns))]
                    else:
                        df.columns = [f'col_{i}' for i in range(len(df.columns))]
            
            # Clean data - handle NaN values properly
            for col in df.columns:
                df[col] = df[col].where(pd.notna(df[col]), None)
            
            if debug:
                print(f"Chunk {chunk_id} processed: {len(df)} rows with {len(df.columns)} columns")
            return df
            
        except Exception as e:
            print(f"Error processing chunk {chunk_id}: {e}")
            return pd.DataFrame()

    def _process_chunk(self, chunk_info: Tuple[int, int, str, Optional[int], Dict[str, Any], List[str]]) -> pd.DataFrame:
        """
        Process a single chunk of the file in parallel.
        
        Args:
            chunk_info: Tuple of (start_line, end_line, file_path, limit, column_mapping, column_names)
            
        Returns:
            DataFrame with processed chunk data
        """
        start_line, end_line, file_path, limit, column_mapping, column_names = chunk_info
        chunk_id = start_line // 50000 + 1
        
        try:
            if debug:
                print(f"Processing chunk {chunk_id}: lines {start_line}-{end_line}")
            
            # Read chunk with pandas - handle header row properly
            if start_line == 0:
                # First chunk: include header row
                df = pd.read_csv(
                    file_path,
                    sep='\t',
                    encoding='latin-1',
                    skiprows=0,
                    nrows=end_line - start_line + 1,  # +1 to include header
                    low_memory=False,
                    on_bad_lines='skip',
                    header=0  # Use header row
                )
            else:
                # Subsequent chunks: skip header row and use complete column names
                df = pd.read_csv(
                    file_path,
                    sep='\t',
                    encoding='latin-1',
                    skiprows=start_line + 1,  # +1 for header
                    nrows=end_line - start_line,
                    low_memory=False,
                    on_bad_lines='skip',
                    header=None  # No header row
                )
                # Set column names using the complete header we loaded
                if column_names and len(column_names) >= len(df.columns):
                    df.columns = column_names[:len(df.columns)]
                else:
                    # Fallback: pad with generic names if needed
                    if column_names:
                        df.columns = column_names[:len(df.columns)] + [f'col_{i}' for i in range(len(column_names), len(df.columns))]
                    else:
                        df.columns = [f'col_{i}' for i in range(len(df.columns))]
            
            # Clean data - handle NaN values properly
            for col in df.columns:
                df[col] = df[col].where(pd.notna(df[col]), None)
            
            if debug:
                print(f"Chunk {chunk_id} processed: {len(df)} rows with {len(df.columns)} columns")
            return df
            
        except Exception as e:
            print(f"Error processing chunk {chunk_id}: {e}")
            return pd.DataFrame()
    
    def _get_file_chunks(self, file_path: str, limit: Optional[int] = None) -> List[Tuple[int, int, str, Optional[int], Dict[str, Any], List[str]]]:
        """
        Calculate file chunks for parallel processing.
        
        Args:
            file_path: Path to the L2 file
            limit: Maximum number of rows to process
            
        Returns:
            List of (start_line, end_line, file_path, limit, column_mapping, column_names) tuples
        """
        # Load complete header first
        print("Loading complete header from file...")
        column_names, column_order = self._load_complete_header(file_path)
        
        if not column_names:
            raise ValueError("Failed to load header from file")
        
        # Count total lines
        with open(file_path, 'rb') as f:
            total_lines = sum(1 for _ in f) - 1  # Subtract header row
        
        if limit:
            total_lines = min(total_lines, limit)
        
        print(f"Total lines to process: {total_lines:,}")
        
        # Create chunks
        chunk_size = 50000  # 50k rows per chunk
        chunks = []
        
        for i in range(0, total_lines, chunk_size):
            start_line = i
            end_line = min(i + chunk_size, total_lines)
            chunks.append((start_line, end_line, file_path, limit, self.column_mapping, column_names))
        
        print(f"Created {len(chunks)} chunks for parallel processing")
        return chunks
    
    def read_l2_file_parallel(self, file_path: str, limit: Optional[int] = None, num_workers: int = None) -> pd.DataFrame:
        """
        Read L2 data file using parallel processing.
        
        Args:
            file_path: Path to the .tab file
            limit: Maximum number of rows to read (None for all)
            num_workers: Number of parallel workers (default: CPU count)
            
        Returns:
            DataFrame with L2 data
        """
        print(f"Reading L2 data from: {os.path.basename(file_path)}")
        
        if num_workers is None:
            num_workers = mp.cpu_count()
        
        print(f"Using {num_workers} parallel workers")
        
        # Get file chunks
        chunks = self._get_file_chunks(file_path, limit)
        
        # Process chunks in parallel
        all_data = []
        with Pool(processes=num_workers) as pool:
            # Process chunks with progress bar
            with tqdm(total=len(chunks), desc="Processing chunks", unit="chunk") as pbar:
                for result in pool.imap(self._process_chunk, chunks):
                    if not result.empty:
                        all_data.append(result)
                    pbar.update(1)
        
        if not all_data:
            print("No data processed")
            return pd.DataFrame()
        
        # Combine all chunks
        print("Combining chunks...")
        df = pd.concat(all_data, ignore_index=True)
        
        # Apply limit if specified
        if limit and len(df) > limit:
            df = df.head(limit)
        
        print(f"Loaded {len(df):,} rows with {len(df.columns)} columns")
        return df
    
    
    def _insert_into_table_batched(self, cursor, df: pd.DataFrame, table_type: str, 
                                  columns: List[str], col_map: Dict[str, str], batch_size: int):
        """Insert data into a single table using batched insertions."""
        if not columns:
            return
        
        table_name = f"l2_{table_type}"
        print(f"  Inserting into {table_name}...")
        
        
        # Prepare data for batch insert
        batch_data = []
        for _, row in df.iterrows():
            lvid = str(row.get('LALVOTERID') or '')
            if not lvid or lvid == 'None':
                continue
            
            values = [lvid]
            for col in columns:
                val = row.get(col)
                if pd.isna(val):
                    values.append(None)
                else:
                    # Convert date fields to MySQL format (YYYY-MM-DD)
                    if col in ['Voters_BirthDate', 'Voters_CalculatedRegDate', 'Voters_OfficialRegDate', 'Voters_MovedFrom_Date']:
                        try:
                            # Convert MM/DD/YYYY to YYYY-MM-DD
                            if isinstance(val, str) and '/' in val:
                                from datetime import datetime
                                date_obj = datetime.strptime(val, '%m/%d/%Y')
                                values.append(date_obj.strftime('%Y-%m-%d'))
                            else:
                                values.append(str(val))
                        except (ValueError, TypeError):
                            values.append(None)
                    elif self._is_boolean_field(col):
                        values.append(self._coerce_bool(val))
                    else:
                        values.append(str(val))
            
            batch_data.append(tuple(values))
        
        if not batch_data:
            print(f"    No data to insert into {table_name}")
            return
        
        # Insert in batches
        db_columns = ['LALVOTERID'] + [f"`{col_map[col]}`" for col in columns]
        placeholders = ', '.join(['%s'] * len(db_columns))
        sql = f"REPLACE INTO {table_name} ({', '.join(db_columns)}) VALUES ({placeholders})"
        
        total_inserted = 0
        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i:i + batch_size]
            cursor.executemany(sql, batch)
            total_inserted += len(batch)
            print(f"    {table_name}: {total_inserted:,}/{len(batch_data):,} rows inserted")
        
        print(f"    Inserted {total_inserted:,} rows into {table_name}")
    
    def _insert_geo_data_batched(self, cursor, df: pd.DataFrame, batch_size: int):
        """Insert geographic data (lat/lon) into l2_geo table using batched insertions.
        Ensures ALL records get a row in l2_geo, even if coordinates are missing."""
        print("  Inserting into l2_geo...")
        
        # Prepare data for batch insert - process ALL records
        batch_data = []
        for _, row in df.iterrows():
            lvid = str(row.get('LALVOTERID') or '')
            if not lvid:
                continue
            
            # Extract latitude and longitude
            lat = row.get('Residence_Addresses_Latitude')
            lon = row.get('Residence_Addresses_Longitude')
            
            # Convert to float if possible, but always include the record
            try:
                lat = float(lat) if lat and not pd.isna(lat) else None
                lon = float(lon) if lon and not pd.isna(lon) else None
            except (ValueError, TypeError):
                lat = None
                lon = None
            
            # Always add the record, even if coordinates are None
            batch_data.append((lvid, lat, lon))
        
        if not batch_data:
            print("    No geo data to insert")
            return
        
        # Insert in batches
        sql = "REPLACE INTO l2_geo (LALVOTERID, latitude, longitude) VALUES (%s, %s, %s)"
        
        total_inserted = 0
        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i:i + batch_size]
            cursor.executemany(sql, batch)
            total_inserted += len(batch)
            print(f"    l2_geo: {total_inserted:,}/{len(batch_data):,} rows inserted")
        
        print(f"    Inserted {total_inserted:,} rows into l2_geo")
    
    def _insert_partitioned_data_batched(self, cursor, df: pd.DataFrame, table_type: str, 
                                        columns: List[str], col_map: Dict[str, str], batch_size: int):
        """Insert data into partitioned tables (political or other) using batched insertions.
        Ensures ALL records get a row in every table, even if some fields are missing."""
        if not columns:
            return
        
        # Split into chunks of 120 columns (MySQL limit)
        chunks = [columns[i:i + 120] for i in range(0, len(columns), 120)]
        
        for chunk_idx, chunk in enumerate(chunks, 1):
            table_name = f"l2_{table_type}_part_{chunk_idx}"
            print(f"  Inserting into {table_name}...")
            
            # Prepare data for batch insert - process ALL records
            batch_data = []
            for _, row in df.iterrows():
                lvid = str(row.get('LALVOTERID') or '')
                if not lvid:
                    continue
                
                values = [lvid]  # Always include LALVOTERID
                for col in chunk:
                    val = row.get(col)
                    if pd.isna(val):
                        values.append(None)
                    elif self._is_boolean_field(col):
                        values.append(self._coerce_bool(val))
                    else:
                        values.append(str(val))
                
                # Always add the record, even if some fields are None
                batch_data.append(tuple(values))
            
            if not batch_data:
                print(f"    No data to insert into {table_name}")
                continue
            
            # Insert in batches
            db_columns = ['LALVOTERID'] + [f"`{col_map[col]}`" for col in chunk]
            placeholders = ', '.join(['%s'] * len(db_columns))
            sql = f"REPLACE INTO {table_name} ({', '.join(db_columns)}) VALUES ({placeholders})"
            
            total_inserted = 0
            for i in range(0, len(batch_data), batch_size):
                batch = batch_data[i:i + batch_size]
                cursor.executemany(sql, batch)
                total_inserted += len(batch)
                print(f"    {table_name}: {total_inserted:,}/{len(batch_data):,} rows inserted")
            
            print(f"    Inserted {total_inserted:,} rows into {table_name}")
    
    def _is_boolean_field(self, source_column_name: str) -> bool:
        """Return True if the given source column should be treated as boolean.
        Includes election flags and consumer donor political flags.
        """
        try:
            name = str(source_column_name)
        except Exception:
            return False

        upper_name = name.upper()
        if upper_name in {"CONSUMERDATA_DONOR_POLITICAL_CONSERVATIVE", "CONSUMERDATA_DONOR_POLITICAL_LIBERAL"}:
            return True

        import re
        return re.match(r"^(ANYELECTION|GENERAL|PRIMARY|OTHERELECTION|PRESIDENTIALPRIMARY)_\d{4}$", upper_name) is not None

    def _coerce_bool(self, value):
        """Map Y/N-like inputs to 1/0/NULL for BOOLEAN columns."""
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
    
    def load_state_data(self, state: str, limit: Optional[int] = None, 
                       num_workers: int = None, batch_size: int = 100000):
        """
        Load L2 data for a specific state using parallel processing and batched insertions.
        
        Args:
            state: Two-letter state code
            limit: Maximum number of records to load (None for all)
            num_workers: Number of parallel workers (default: CPU count)
            batch_size: Number of rows to insert per batch (default: 100,000)
        """
        print(f"Starting L2 data load for state: {state}")
        if limit:
            print(f"Limit: {limit:,} records")
        else:
            print("Loading all available records")
        
        print(f"Workers: {num_workers or mp.cpu_count()}")
        print(f"Batch size: {batch_size:,}")
        
        # Find the state file
        file_path = self.find_state_file(state)
        if not file_path:
            return False
        
        try:
            # Load column mapping
            self.load_column_mapping()
            
            # Read L2 data file using simple sequential processing for single state
            start_time = time.time()
            df = self._read_l2_file_standalone(file_path, limit, self.debug)
            read_time = time.time() - start_time
            
            if df.empty:
                print("No data to load")
                return False
            
            print(f"File reading completed in {read_time:.2f} seconds")
            
            # Use vectorized operations for database insertion
            db_config = self._get_database_config()
            print(f"Using {db_config['target'].upper()} database ({db_config['host']}:{db_config['port']})")
            
            # Insert data using vectorized operations
            insert_start = time.time()
            self._insert_data_with_connection(None, df, batch_size)
            insert_time = time.time() - insert_start
            
            print(f"Database insertion completed in {insert_time:.2f} seconds")
            print(f"Successfully loaded L2 data for {state}")
            print(f"Total time: {read_time + insert_time:.2f} seconds")
            print(f"Speed: {len(df) / (read_time + insert_time):,.0f} rows/second")
            return True
            
        except Exception as e:
            print(f"Error loading L2 data for {state}: {e}")
            return False
    
    def load_multiple_states(self, states: List[str], limit: Optional[int] = None, 
                           batch_size: int = 100000, num_workers: int = None) -> Dict[str, bool]:
        """
        Load L2 data for multiple states.
        
        Args:
            states: List of state codes to process
            limit: Maximum number of rows per state
            batch_size: Number of rows to insert per batch
            num_workers: Number of parallel workers for file processing
            
        Returns:
            Dictionary mapping state codes to success status
        """
        results = {}
        total_states = len(states)
        
        print(f"Processing {total_states} states: {', '.join(states)}")
        if limit:
            print(f"Limit: {limit:,} records per state")
        print(f"Workers: {num_workers or mp.cpu_count()}")
        print(f"Batch size: {batch_size:,}")
        print("-" * 50)
        
        for i, state in enumerate(states, 1):
            print(f"\n[{i}/{total_states}] Processing state: {state}")
            print("=" * 30)
            
            try:
                success = self.load_state_data(state, limit, num_workers, batch_size)
                results[state] = success
                
                if success:
                    print(f"[SUCCESS] {state} completed successfully")
                else:
                    print(f"[FAILED] {state} failed")
                    
            except Exception as e:
                print(f"[ERROR] {state} failed with error: {e}")
                results[state] = False
        
        # Summary
        print("\n" + "=" * 50)
        print("PROCESSING SUMMARY")
        print("=" * 50)
        
        successful = sum(1 for success in results.values() if success)
        failed = total_states - successful
        
        print(f"Total states processed: {total_states}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        
        if failed > 0:
            failed_states = [state for state, success in results.items() if not success]
            print(f"Failed states: {', '.join(failed_states)}")
        
        return results
    
    def _insert_data_with_connection(self, connection, df: pd.DataFrame, batch_size: int = 100000):
        """
        Insert L2 data into the appropriate database tables using vectorized operations.
        
        Args:
            connection: Database connection to use (for compatibility, not used with new system)
            df: DataFrame with L2 data
            batch_size: Number of rows to insert per batch
        """
        if df.empty:
            print("No data to insert")
            return
        
        print(f"Inserting data into L2 tables using vectorized operations (batch size: {batch_size:,})...")
        
        try:
            # Use the L2 data manager for vectorized operations
            results = self.l2_manager.process_l2_dataframe(df)
            
            total_rows = 0
            for table, result in results.items():
                if result.success:
                    print(f"  [SUCCESS] {table}: {result.row_count:,} rows inserted in {result.execution_time:.2f}s")
                    total_rows += result.row_count
                else:
                    print(f"  [FAILED] {table}: {result.error}")
            
            print(f"Successfully inserted {total_rows:,} total rows into L2 tables")
            
        except Exception as e:
            print(f"Error inserting data: {e}")
            raise
    
    def _worker_process_chunk(self, chunk_info: Tuple[str, int, int, str, Optional[int], Dict[str, Any], List[str]], 
                             batch_size: int, debug: bool = False) -> Dict[str, Any]:
        """
        Worker function that processes a single chunk of data - reads chunk and inserts into database.
        This runs in a separate process to avoid memory issues.
        
        Args:
            chunk_info: Tuple containing (state, start_line, end_line, file_path, limit, column_mapping, column_names)
            batch_size: Database batch size
            debug: Enable debug mode
            
        Returns:
            Dictionary with processing results
        """
        state, start_line, end_line, file_path, limit, column_mapping, column_names = chunk_info
        
        try:
            if not debug:
                print(f"[Worker] Processing chunk for {state}: lines {start_line}-{end_line}")
            
            start_time = time.time()
            
            # Read the chunk data directly without creating a full loader instance
            df = self._process_chunk_standalone((start_line, end_line, file_path, limit, column_mapping, column_names), debug)
            
            if df.empty:
                return {
                    'state': state,
                    'chunk': f"{start_line}-{end_line}",
                    'success': False,
                    'error': 'No data loaded from chunk',
                    'rows_processed': 0,
                    'processing_time': time.time() - start_time
                }
            
            # Insert data into database using vectorized operations
            # Create database managers locally in the worker process
            try:
                from Database.l2_data_manager import get_l2_data_manager
                l2_manager = get_l2_data_manager()
                
                if not debug:
                    print(f"[Worker] Inserting chunk data for {state}")
                
                results = l2_manager.process_l2_dataframe(df)
                
                total_rows = 0
                for table, result in results.items():
                    if result.success:
                        total_rows += result.row_count
                    else:
                        print(f"[Worker] Error inserting into {table}: {result.error}")
                
                processing_time = time.time() - start_time
                
                if not debug:
                    print(f"[Worker] Completed {state} chunk {start_line}-{end_line}: {len(df):,} rows in {processing_time:.2f}s")
                
                return {
                    'state': state,
                    'chunk': f"{start_line}-{end_line}",
                    'success': True,
                    'error': None,
                    'rows_processed': len(df),
                    'processing_time': processing_time
                }
                
            except Exception as db_error:
                processing_time = time.time() - start_time
                print(f"[Worker] Database error for {state} chunk {start_line}-{end_line}: {db_error}")
                return {
                    'state': state,
                    'chunk': f"{start_line}-{end_line}",
                    'success': False,
                    'error': f"Database error: {str(db_error)}",
                    'rows_processed': 0,
                    'processing_time': processing_time
                }
                
        except Exception as e:
            processing_time = time.time() - start_time if 'start_time' in locals() else 0
            print(f"[Worker] Error processing {state} chunk {start_line}-{end_line}: {e}")
            return {
                'state': state,
                'chunk': f"{start_line}-{end_line}",
                'success': False,
                'error': str(e),
                'rows_processed': 0,
                'processing_time': processing_time
            }
    
    def _worker_process_state(self, state: str, limit: Optional[int], batch_size: int, debug: bool = False) -> Dict[str, Any]:
        """
        Worker function that processes a single state - reads data and inserts into database.
        This runs in a separate process to avoid memory issues.
        
        Args:
            state: State code to process
            limit: Maximum number of records to load
            batch_size: Database batch size
            
        Returns:
            Dictionary with processing results
        """
        try:
            if not debug:
                print(f"[Worker] Starting processing for state: {state}")
            
            # Find the file for this state (without creating a full loader instance)
            l2_data_dir = os.getenv("L2_DATA_DIR")
            if not l2_data_dir:
                return {
                    'state': state,
                    'success': False,
                    'error': 'L2_DATA_DIR environment variable not set',
                    'rows_processed': 0,
                    'processing_time': 0
                }
            
            # Look for files with the pattern: *VM2Uniform*{state}*.tab
            pattern = f"*VM2Uniform*{state.upper()}*.tab"
            files = glob.glob(os.path.join(l2_data_dir, pattern))
            
            if not files:
                return {
                    'state': state,
                    'success': False,
                    'error': f'File not found for state {state}',
                    'rows_processed': 0,
                    'processing_time': 0
                }
            
            file_path = files[0]
            start_time = time.time()
            
            # Read the data using standalone method
            df = self._read_l2_file_standalone(file_path, limit, debug)
            
            if df.empty:
                return {
                    'state': state,
                    'success': False,
                    'error': 'No data loaded',
                    'rows_processed': 0,
                    'processing_time': time.time() - start_time
                }
            
            # Insert data into database using vectorized operations
            try:
                from Database.l2_data_manager import get_l2_data_manager
                l2_manager = get_l2_data_manager()
                
                if not debug:
                    print(f"[Worker] Inserting data for {state}")
                
                results = l2_manager.process_l2_dataframe(df)
                
                total_rows = 0
                for table, result in results.items():
                    if result.success:
                        total_rows += result.row_count
                    else:
                        print(f"[Worker] Error inserting into {table}: {result.error}")
                
                processing_time = time.time() - start_time
                
                if not debug:
                    print(f"[Worker] Completed {state}: {len(df):,} rows in {processing_time:.2f}s")
                
                return {
                    'state': state,
                    'success': True,
                    'error': None,
                    'rows_processed': len(df),
                    'processing_time': processing_time
                }
                
            except Exception as db_error:
                processing_time = time.time() - start_time
                print(f"[Worker] Database error for {state}: {db_error}")
                return {
                    'state': state,
                    'success': False,
                    'error': f"Database error: {str(db_error)}",
                    'rows_processed': 0,
                    'processing_time': processing_time
                }
                
        except Exception as e:
            processing_time = time.time() - start_time if 'start_time' in locals() else 0
            print(f"[Worker] Error processing {state}: {e}")
            return {
                'state': state,
                'success': False,
                'error': str(e),
                'rows_processed': 0,
                'processing_time': processing_time
            }
    
    def load_multiple_states_parallel(self, states: List[str], limit: Optional[int] = None,
                                    batch_size: int = 100000, max_workers: int = None, debug: bool = False) -> Dict[str, bool]:
        """
        Load multiple states using parallel processing with worker-based approach.
        Each worker handles both file reading and database insertion.
        
        Args:
            states: List of state codes to process
            limit: Maximum number of records per state
            batch_size: Database batch size
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dictionary mapping state codes to success status
        """
        if not states:
            print("No states to process")
            return {}
        
        if max_workers is None:
            max_workers = min(len(states), mp.cpu_count())
        
        print(f"Processing {len(states)} states with {max_workers} workers")
        print(f"States: {', '.join(states)}")
        if limit:
            print(f"Limit: {limit:,} records per state")
        print(f"Batch size: {batch_size:,}")
        print("-" * 60)
        
        results = {}
        start_time = time.time()
        
        # Use ThreadPoolExecutor for I/O bound operations (file reading + DB insertion)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all state processing tasks
            future_to_state = {
                executor.submit(self._worker_process_state, state, limit, batch_size, debug): state 
                for state in states
            }
            
            # Process completed tasks as they finish
            completed = 0
            for future in as_completed(future_to_state):
                state = future_to_state[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[state] = result['success']
                    
                    if result['success']:
                        print(f"[{completed}/{len(states)}] [SUCCESS] {state}: {result['rows_processed']:,} rows in {result['processing_time']:.2f}s")
                    else:
                        print(f"[{completed}/{len(states)}] [FAILED] {state}: {result['error']}")
                        
                except Exception as e:
                    print(f"[{completed}/{len(states)}] [ERROR] {state}: Unexpected error - {e}")
                    results[state] = False
        
        # Summary
        total_time = time.time() - start_time
        successful = sum(1 for success in results.values() if success)
        failed = len(results) - successful
        
        print("\n" + "=" * 60)
        print("PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Total states processed: {len(states)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Average time per state: {total_time/len(states):.2f} seconds")
        
        if failed > 0:
            failed_states = [state for state, success in results.items() if not success]
            print(f"Failed states: {', '.join(failed_states)}")
        
        return results
    
    def load_multiple_states_chunk_parallel(self, states: List[str], limit: Optional[int] = None,
                                          batch_size: int = 100000, max_workers: int = None, 
                                          chunk_size: int = 50000, debug: bool = False) -> Dict[str, bool]:
        """
        Load multiple states using chunk-based parallel processing.
        Each worker processes a single chunk, allowing maximum parallelization.
        
        Args:
            states: List of state codes to process
            limit: Maximum number of records per state
            batch_size: Database batch size
            max_workers: Maximum number of parallel workers
            chunk_size: Size of each chunk for file reading
            debug: Enable debug mode
            
        Returns:
            Dictionary mapping state codes to success status
        """
        if not states:
            print("No states to process")
            return {}
        
        if max_workers is None:
            max_workers = mp.cpu_count()
        
        print(f"Processing {len(states)} states with chunk-based parallel processing")
        print(f"States: {', '.join(states)}")
        if limit:
            print(f"Limit: {limit:,} records per state")
        print(f"Chunk size: {chunk_size:,}")
        print(f"Max workers: {max_workers}")
        print(f"Batch size: {batch_size:,}")
        print("-" * 60)
        
        # Prepare all chunks for all states
        all_chunks = []
        state_results = {state: {'success': True, 'chunks_processed': 0, 'total_rows': 0} for state in states}
        
        for state in states:
            file_path = self.find_state_file(state)
            if not file_path:
                print(f"File not found for state: {state}")
                state_results[state] = {'success': False, 'chunks_processed': 0, 'total_rows': 0}
                continue
            
            # Get file info and create chunks
            with self._debug_timer(f"Preparing chunks for {state}"):
                file_size = self._get_file_size(file_path)
                total_lines = min(limit, file_size) if limit else file_size
                
                # Load header once for this state
                column_names, column_mapping = self._load_complete_header(file_path)
                
                # Create chunks
                chunks = []
                for start_line in range(0, total_lines, chunk_size):
                    end_line = min(start_line + chunk_size - 1, total_lines - 1)
                    chunk_info = (state, start_line, end_line, file_path, limit, column_mapping, column_names)
                    chunks.append(chunk_info)
                
                all_chunks.extend(chunks)
                print(f"Created {len(chunks)} chunks for {state}")
        
        if not all_chunks:
            print("No chunks to process")
            return {state: False for state in states}
        
        print(f"Total chunks to process: {len(all_chunks)}")
        
        # Process chunks in parallel
        results = {}
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all chunk processing tasks
            future_to_chunk = {
                executor.submit(self._worker_process_chunk, chunk_info, batch_size, debug): chunk_info 
                for chunk_info in all_chunks
            }
            
            # Process completed chunks as they finish
            completed = 0
            for future in as_completed(future_to_chunk):
                chunk_info = future_to_chunk[future]
                state = chunk_info[0]
                completed += 1
                
                try:
                    result = future.result()
                    state_results[state]['chunks_processed'] += 1
                    state_results[state]['total_rows'] += result['rows_processed']
                    
                    if not result['success']:
                        state_results[state]['success'] = False
                        print(f"[{completed}/{len(all_chunks)}] [FAILED] {state} chunk {result['chunk']}: {result['error']}")
                    else:
                        if not debug:
                            print(f"[{completed}/{len(all_chunks)}] [SUCCESS] {state} chunk {result['chunk']}: {result['rows_processed']:,} rows in {result['processing_time']:.2f}s")
                        
                except Exception as e:
                    state_results[state]['success'] = False
                    print(f"[{completed}/{len(all_chunks)}] [ERROR] {state} chunk: Unexpected error - {e}")
        
        # Convert to simple success/failure per state
        for state in states:
            results[state] = state_results[state]['success']
        
        # Summary
        total_time = time.time() - start_time
        successful_states = sum(1 for success in results.values() if success)
        failed_states = len(results) - successful_states
        total_chunks = sum(state_results[state]['chunks_processed'] for state in states)
        total_rows = sum(state_results[state]['total_rows'] for state in states)
        
        print("\n" + "=" * 60)
        print("CHUNK-BASED PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Total states processed: {len(states)}")
        print(f"Successful states: {successful_states}")
        print(f"Failed states: {failed_states}")
        print(f"Total chunks processed: {total_chunks}")
        print(f"Total rows processed: {total_rows:,}")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Average time per chunk: {total_time/total_chunks:.2f} seconds" if total_chunks > 0 else "")
        print(f"Processing speed: {total_rows/total_time:,.0f} rows/second" if total_time > 0 else "")
        
        if failed_states > 0:
            failed_state_list = [state for state, success in results.items() if not success]
            print(f"Failed states: {', '.join(failed_state_list)}")
        
        return results
    
    def load_multiple_states_dynamic_chunks(self, states: List[str], limit: Optional[int] = None,
                                          batch_size: int = 100000, max_workers: int = None, 
                                          chunk_size: int = 50000, debug: bool = False) -> Dict[str, bool]:
        """
        Load multiple states using dynamic chunk-based parallel processing.
        Estimates file sizes, creates optimal chunks, and distributes workers across all chunks.
        
        Args:
            states: List of state codes to process
            limit: Maximum number of records per state
            batch_size: Database batch size
            max_workers: Maximum number of parallel workers
            chunk_size: Target size of each chunk for file reading
            debug: Enable debug mode
            
        Returns:
            Dictionary mapping state codes to success status
        """
        if not states:
            print("No states to process")
            return {}
        
        if max_workers is None:
            max_workers = mp.cpu_count()
        
        print(f"Processing {len(states)} states with dynamic chunk-based parallel processing")
        print(f"States: {', '.join(states)}")
        if limit:
            print(f"Limit: {limit:,} records per state")
        print(f"Target chunk size: {chunk_size:,} rows")
        print(f"Max workers: {max_workers}")
        print(f"Batch size: {batch_size:,}")
        print("-" * 60)
        
        # Step 1: Estimate file sizes and create chunks for all states
        all_chunks = []
        state_results = {state: {'success': True, 'chunks_processed': 0, 'total_rows': 0} for state in states}
        
        with self._debug_timer("Estimating file sizes and creating chunks"):
            for state in states:
                file_path = self.find_state_file(state)
                if not file_path:
                    print(f"File not found for state: {state}")
                    state_results[state] = {'success': False, 'chunks_processed': 0, 'total_rows': 0}
                    continue
                
                # Estimate rows in this file
                estimated_rows = self._estimate_rows_per_file(file_path)
                if estimated_rows == 0:
                    print(f"Could not estimate rows for {state}")
                    state_results[state] = {'success': False, 'chunks_processed': 0, 'total_rows': 0}
                    continue
                
                # Apply limit if specified
                if limit:
                    estimated_rows = min(estimated_rows, limit)
                
                # Load header once for this state
                column_names, column_mapping = self._load_complete_header(file_path)
                
                # Create chunks for this file
                chunks_for_state = []
                for start_line in range(0, estimated_rows, chunk_size):
                    end_line = min(start_line + chunk_size - 1, estimated_rows - 1)
                    chunk_info = (state, start_line, end_line, file_path, limit, column_mapping, column_names)
                    chunks_for_state.append(chunk_info)
                
                all_chunks.extend(chunks_for_state)
                print(f"Created {len(chunks_for_state)} chunks for {state} (estimated {estimated_rows:,} rows)")
        
        if not all_chunks:
            print("No chunks to process")
            return {state: False for state in states}
        
        print(f"Total chunks to process: {len(all_chunks)}")
        print(f"Workers will be distributed across all chunks from all files")
        
        # Step 2: Process chunks in parallel with dynamic worker distribution
        results = {}
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all chunk processing tasks
            future_to_chunk = {
                executor.submit(self._worker_process_chunk, chunk_info, batch_size, debug): chunk_info 
                for chunk_info in all_chunks
            }
            
            # Process completed chunks as they finish
            completed = 0
            for future in as_completed(future_to_chunk):
                chunk_info = future_to_chunk[future]
                state = chunk_info[0]
                completed += 1
                
                try:
                    result = future.result()
                    state_results[state]['chunks_processed'] += 1
                    state_results[state]['total_rows'] += result['rows_processed']
                    
                    if not result['success']:
                        state_results[state]['success'] = False
                        print(f"[{completed}/{len(all_chunks)}] [FAILED] {state} chunk {result['chunk']}: {result['error']}")
                    else:
                        if not debug:
                            print(f"[{completed}/{len(all_chunks)}] [SUCCESS] {state} chunk {result['chunk']}: {result['rows_processed']:,} rows in {result['processing_time']:.2f}s")
                        
                except Exception as e:
                    state_results[state]['success'] = False
                    print(f"[{completed}/{len(all_chunks)}] [ERROR] {state} chunk: Unexpected error - {e}")
        
        # Convert to simple success/failure per state
        for state in states:
            results[state] = state_results[state]['success']
        
        # Summary
        total_time = time.time() - start_time
        successful_states = sum(1 for success in results.values() if success)
        failed_states = len(results) - successful_states
        total_chunks = sum(state_results[state]['chunks_processed'] for state in states)
        total_rows = sum(state_results[state]['total_rows'] for state in states)
        
        print("\n" + "=" * 60)
        print("DYNAMIC CHUNK-BASED PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Total states processed: {len(states)}")
        print(f"Successful states: {successful_states}")
        print(f"Failed states: {failed_states}")
        print(f"Total chunks processed: {total_chunks}")
        print(f"Total rows processed: {total_rows:,}")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Average time per chunk: {total_time/total_chunks:.2f} seconds" if total_chunks > 0 else "")
        print(f"Processing speed: {total_rows/total_time:,.0f} rows/second" if total_time > 0 else "")
        
        if failed_states > 0:
            failed_state_list = [state for state, success in results.items() if not success]
            print(f"Failed states: {', '.join(failed_state_list)}")
        
        return results
    
    def load_multiple_states_chunked(self, states: List[str], limit: Optional[int] = None,
                                   batch_size: int = 100000, max_workers: int = None, 
                                   debug: bool = False) -> Dict[str, bool]:
        """
        Load multiple states using chunk-based processing.
        Processes one file at a time with multiple workers reading chunks in parallel.
        
        Args:
            states: List of state codes to process
            limit: Maximum number of records per state
            batch_size: Number of rows per chunk and database batch
            max_workers: Maximum number of parallel workers
            debug: Enable debug mode
            
        Returns:
            Dictionary mapping state codes to success status
        """
        if not states:
            print("No states to process")
            return {}
        
        if max_workers is None:
            max_workers = min(8, mp.cpu_count())  # Cap at 8 workers
        
        print(f"Processing {len(states)} states with chunk-based parallel processing")
        if limit:
            print(f"Limit: {limit:,} records per state")
        print(f"Batch size: {batch_size:,}, Max workers: {max_workers}")
        if debug:
            print(f"States: {', '.join(states)}")
        print("-" * 60)
        
        results = {}
        total_start_time = time.time()
        
        # Process each state sequentially, but with parallel chunk reading within each state
        for state_idx, state in enumerate(states, 1):
            print(f"\n[{state_idx}/{len(states)}] Processing {state}")
            if debug:
                print("=" * 40)
            
            state_start_time = time.time()
            
            try:
                # Find the file for this state
                file_path = self.find_state_file(state)
                if not file_path:
                    print(f"[ERROR] File not found for state: {state}")
                    results[state] = False
                    continue
                
                # Process this state with chunked parallel reading
                success = self._process_state_chunked(
                    state=state,
                    file_path=file_path,
                    limit=limit,
                    batch_size=batch_size,
                    max_workers=max_workers,
                    debug=debug
                )
                
                state_time = time.time() - state_start_time
                results[state] = success
                
                if success:
                    print(f"[SUCCESS] {state} ({state_time:.1f}s)")
                else:
                    print(f"[FAILED] {state} ({state_time:.1f}s)")
                    
            except Exception as e:
                state_time = time.time() - state_start_time
                print(f"[ERROR] {state} failed with error: {e} (after {state_time:.2f}s)")
                results[state] = False
        
        # Summary
        total_time = time.time() - total_start_time
        successful = sum(1 for success in results.values() if success)
        failed = len(results) - successful
        
        print(f"\nSUMMARY: {successful}/{len(states)} states completed in {total_time:.1f}s")
        if failed > 0:
            failed_states = [state for state, success in results.items() if not success]
            print(f"Failed: {', '.join(failed_states)}")
        
        return results
    
    def _process_state_chunked(self, state: str, file_path: str, limit: Optional[int] = None,
                             batch_size: int = 100000, max_workers: int = 8, 
                             debug: bool = False) -> bool:
        """
        Process a single state file using chunked parallel reading.
        
        Args:
            state: State code being processed
            file_path: Path to the state file
            limit: Maximum number of records to process
            batch_size: Number of rows per chunk
            max_workers: Number of parallel workers for chunk reading
            debug: Enable debug mode
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if debug:
                print(f"Processing {state} file: {os.path.basename(file_path)}")
            
            # Load column mapping
            self.load_column_mapping()
            
            # Get file info and create chunks
            with self._debug_timer(f"Preparing chunks for {state}"):
                # Count total lines
                with open(file_path, 'rb') as f:
                    total_lines = sum(1 for _ in f) - 1  # Subtract header row
                
                if limit:
                    total_lines = min(total_lines, limit)
                
                if debug:
                    print(f"Total lines to process: {total_lines:,}")
                
                # Load header once
                column_names, column_mapping = self._load_complete_header_standalone(file_path)
                
                # Create chunks
                chunks = []
                for start_line in range(0, total_lines, batch_size):
                    end_line = min(start_line + batch_size - 1, total_lines - 1)
                    chunk_info = (state, start_line, end_line, file_path, limit, column_mapping, column_names)
                    chunks.append(chunk_info)
                
                if debug:
                    print(f"Created {len(chunks)} chunks for {state}")
            
            if not chunks:
                print(f"No chunks to process for {state}")
                return False
            
            # Process chunks in parallel with progress tracking
            total_rows_processed = 0
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all chunk processing tasks
                future_to_chunk = {
                    executor.submit(self._worker_process_chunk_optimized, chunk_info, batch_size, debug): chunk_info 
                    for chunk_info in chunks
                }
                
                # Process completed chunks with progress bar
                with tqdm(total=len(chunks), desc=f"{state}", unit="chunk") as pbar:
                    for future in as_completed(future_to_chunk):
                        chunk_info = future_to_chunk[future]
                        chunk_state = chunk_info[0]
                        
                        try:
                            result = future.result()
                            if result['success']:
                                total_rows_processed += result['rows_processed']
                                if debug:
                                    print(f"[{state}] Chunk {result['chunk']}: {result['rows_processed']:,} rows in {result['processing_time']:.2f}s")
                            else:
                                print(f"[{state}] Chunk {result['chunk']} failed: {result['error']}")
                                return False
                                
                        except Exception as e:
                            print(f"[{state}] Chunk processing error: {e}")
                            return False
                        
                        pbar.update(1)
            
            processing_time = time.time() - start_time
            print(f"[SUCCESS] {state}: {total_rows_processed:,} rows in {processing_time:.1f}s ({total_rows_processed/processing_time:,.0f} rows/s)")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Error processing {state}: {e}")
            return False
    
    def _worker_process_chunk_optimized(self, chunk_info: Tuple[str, int, int, str, Optional[int], Dict[str, Any], List[str]], 
                                      batch_size: int, debug: bool = False) -> Dict[str, Any]:
        """
        Optimized worker function that processes a single chunk and inserts data immediately.
        This runs in a separate process to avoid memory issues.
        
        Args:
            chunk_info: Tuple containing (state, start_line, end_line, file_path, limit, column_mapping, column_names)
            batch_size: Database batch size
            debug: Enable debug mode
            
        Returns:
            Dictionary with processing results
        """
        state, start_line, end_line, file_path, limit, column_mapping, column_names = chunk_info
        
        try:
            start_time = time.time()
            
            # Read the chunk data directly
            df = self._process_chunk_standalone((start_line, end_line, file_path, limit, column_mapping, column_names), debug)
            
            if df.empty:
                return {
                    'state': state,
                    'chunk': f"{start_line}-{end_line}",
                    'success': False,
                    'error': 'No data loaded from chunk',
                    'rows_processed': 0,
                    'processing_time': time.time() - start_time
                }
            
            # Insert data into database immediately (no vectorization)
            try:
                from Database.l2_data_manager import get_l2_data_manager
                l2_manager = get_l2_data_manager()
                
                # Process and insert data directly
                results = l2_manager.process_l2_dataframe(df)
                
                total_rows = 0
                for table, result in results.items():
                    if result.success:
                        total_rows += result.row_count
                        # concise per-table insertion log at worker level
                        if debug:
                            print(f"[Worker][{state}][{start_line}-{end_line}] {table}: +{result.row_count:,} rows in {result.execution_time:.2f}s")
                    else:
                        print(f"[Worker][{state}][{start_line}-{end_line}] {table}: [ERROR] {result.error}")
                
                processing_time = time.time() - start_time
                
                return {
                    'state': state,
                    'chunk': f"{start_line}-{end_line}",
                    'success': True,
                    'error': None,
                    'rows_processed': len(df),
                    'processing_time': processing_time
                }
                
            except Exception as db_error:
                processing_time = time.time() - start_time
                return {
                    'state': state,
                    'chunk': f"{start_line}-{end_line}",
                    'success': False,
                    'error': f"Database error: {str(db_error)}",
                    'rows_processed': 0,
                    'processing_time': processing_time
                }
                
        except Exception as e:
            processing_time = time.time() - start_time if 'start_time' in locals() else 0
            return {
                'state': state,
                'chunk': f"{start_line}-{end_line}",
                'success': False,
                'error': str(e),
                'rows_processed': 0,
                'processing_time': processing_time
            }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Load L2 voter data from files into NAS database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python load_l2_data_to_nas.py --state AK --limit 100
  python load_l2_data_to_nas.py --state CA
  python load_l2_data_to_nas.py --state NY,ME --limit 1000 --workers 8 --batch-size 50000
  python load_l2_data_to_nas.py --state all --limit 1000
  python load_l2_data_to_nas.py --state TX --workers 4 --batch-size 200000
        """
    )
    
    parser.add_argument(
        '--state', 
        required=True,
        help='State code(s): single state (e.g., AK), multiple states (e.g., NY,ME), or "all" for all available states'
    )
    
    parser.add_argument(
        '--limit', 
        type=int,
        help='Maximum number of records to load (default: load all)'
    )
    
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=None,
        help='Number of parallel workers (default: CPU count)'
    )
    
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=50000,
        help='Number of rows per chunk and database batch (default: 50,000)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with detailed timing information'
    )
    
    
    args = parser.parse_args()
    
    # Parse state argument
    if args.state.lower() == 'all':
        # Load all available states
        try:
            loader = L2DataLoader(debug=args.debug)
            available_states = loader.get_available_states()
            
            if not available_states:
                print("No L2 data files found in the data directory")
                sys.exit(1)
            
            print(f"Found {len(available_states)} available states: {', '.join(available_states)}")
            
            # Process all states using chunk-based parallel processing
            results = loader.load_multiple_states_chunked(
                states=available_states,
                limit=args.limit,
                batch_size=args.batch_size,
                max_workers=args.workers,
                debug=args.debug
            )
            
            # Check if all succeeded
            all_successful = all(results.values())
            if all_successful:
                print("All states processed successfully")
                sys.exit(0)
            else:
                print("Some states failed to process")
                sys.exit(1)
                
        except Exception as e:
            print(f"Fatal error: {e}")
            sys.exit(1)
    
    elif ',' in args.state:
        # Multiple states specified
        states = [s.strip().upper() for s in args.state.split(',')]
        
        # Validate each state code
        for state in states:
            if len(state) != 2 or not state.isalpha():
                print(f"Invalid state code: {state}. State codes must be exactly 2 letters")
                sys.exit(1)
        
        try:
            loader = L2DataLoader(debug=args.debug)
            results = loader.load_multiple_states_chunked(
                states=states,
                limit=args.limit,
                batch_size=args.batch_size,
                max_workers=args.workers,
                debug=args.debug
            )
            
            # Check if all succeeded
            all_successful = all(results.values())
            if all_successful:
                print("All specified states processed successfully")
                sys.exit(0)
            else:
                print("Some states failed to process")
                sys.exit(1)
                
        except Exception as e:
            print(f"Fatal error: {e}")
            sys.exit(1)
    
    else:
        # Single state
        if len(args.state) != 2 or not args.state.isalpha():
            print("State code must be exactly 2 letters")
            sys.exit(1)
        
        # For single state, route through chunk-based processing so --workers applies per state
        try:
            loader = L2DataLoader(debug=args.debug)
            results = loader.load_multiple_states_chunked(
                states=[args.state.upper()],
                limit=args.limit,
                batch_size=args.batch_size,
                max_workers=args.workers,
                debug=args.debug
            )

            if all(results.values()):
                print("L2 data loading completed successfully")
                sys.exit(0)
            else:
                print("L2 data loading failed")
                sys.exit(1)
                
        except Exception as e:
            print(f"Fatal error: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()
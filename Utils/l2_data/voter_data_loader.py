#!/usr/bin/env python3
"""
Voter Data Loader Module
Loads and manages L2 voter data from CSV files.
"""

import pandas as pd
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

class VoterDataLoader:
    """
    Loads and manages L2 voter data from CSV files.
    """
    
    def __init__(self, data_file_path: str):
        """
        Initialize the voter data loader.
        
        Args:
            data_file_path (str): Path to the L2 data CSV file
        """
        self.data_file_path = data_file_path
        self.data = None
        self._load_data()
    
    def _load_data(self):
        """Load the L2 data from CSV file."""
        if not os.path.exists(self.data_file_path):
            raise FileNotFoundError(f"L2 data file not found: {self.data_file_path}")
        
        try:
            # Try to detect the delimiter and handle the complex CSV format
            # First, try to read a small sample to detect the format
            with open(self.data_file_path, 'r', encoding='utf-8') as f:
                first_lines = [f.readline().strip() for _ in range(5)]
            
            # Check if it's tab-delimited
            if '\t' in first_lines[0]:
                delimiter = '\t'
                print("Detected tab-delimited format")
            else:
                delimiter = ','
                print("Detected comma-delimited format")
            
            # Load CSV data with appropriate delimiter and handle encoding issues
            self.data = pd.read_csv(
                self.data_file_path,
                delimiter=delimiter,
                encoding='utf-8',
                on_bad_lines='skip',    # Skip problematic lines (newer pandas)
                low_memory=False        # Better handling of large files
            )
            
            print(f"Loaded {len(self.data)} voter records from {self.data_file_path}")
            
            # Validate required columns
            required_columns = ['SEQUENCE', 'LALVOTERID', 'Voters_FirstName', 'Voters_LastName']
            missing_columns = [col for col in required_columns if col not in self.data.columns]
            if missing_columns:
                print(f"Warning: Missing required columns: {missing_columns}")
                print(f"Available columns: {list(self.data.columns[:10])}...")  # Show first 10 columns
                
        except Exception as e:
            raise Exception(f"Failed to load L2 data: {e}")
    
    def get_voter_by_sequence(self, sequence: int) -> Optional[Dict[str, Any]]:
        """
        Get voter data by sequence number.
        
        Args:
            sequence (int): Sequence number to search for
            
        Returns:
            Dict[str, Any]: Voter data dictionary or None if not found
        """
        if self.data is None:
            return None
        
        try:
            # Find voter by sequence number
            voter_data = self.data[self.data['SEQUENCE'] == sequence]
            
            if len(voter_data) == 0:
                print(f"No voter found with sequence {sequence}")
                return None
            
            if len(voter_data) > 1:
                print(f"Warning: Multiple voters found with sequence {sequence}, using first one")
            
            # Convert to dictionary
            voter_dict = voter_data.iloc[0].to_dict()
            
            # Clean up the data
            for key, value in voter_dict.items():
                if pd.isna(value):
                    voter_dict[key] = None
                elif isinstance(value, (int, float)) and pd.isna(value):
                    voter_dict[key] = None
            
            return voter_dict
            
        except Exception as e:
            print(f"Error getting voter by sequence {sequence}: {e}")
            return None
    
    def get_voter_by_lalvoterid(self, lalvoterid: str) -> Optional[Dict[str, Any]]:
        """
        Get voter data by LALVOTERID.
        
        Args:
            lalvoterid (str): LALVOTERID to search for
            
        Returns:
            Dict[str, Any]: Voter data dictionary or None if not found
        """
        if self.data is None:
            return None
        
        try:
            # Find voter by LALVOTERID
            voter_data = self.data[self.data['LALVOTERID'] == lalvoterid]
            
            if len(voter_data) == 0:
                print(f"No voter found with LALVOTERID {lalvoterid}")
                return None
            
            if len(voter_data) > 1:
                print(f"Warning: Multiple voters found with LALVOTERID {lalvoterid}, using first one")
            
            # Convert to dictionary
            voter_dict = voter_data.iloc[0].to_dict()
            
            # Clean up the data
            for key, value in voter_dict.items():
                if pd.isna(value):
                    voter_dict[key] = None
                elif isinstance(value, (int, float)) and pd.isna(value):
                    voter_dict[key] = None
            
            return voter_dict
            
        except Exception as e:
            print(f"Error getting voter by LALVOTERID {lalvoterid}: {e}")
            return None
    
    def get_voter_by_name(self, first_name: str, last_name: str) -> Optional[Dict[str, Any]]:
        """
        Get voter data by first and last name.
        
        Args:
            first_name (str): First name to search for
            last_name (str): Last name to search for
            
        Returns:
            Dict[str, Any]: Voter data dictionary or None if not found
        """
        if self.data is None:
            return None
        
        try:
            # Find voter by name (case-insensitive)
            voter_data = self.data[
                (self.data['Voters_FirstName'].str.lower() == first_name.lower()) &
                (self.data['Voters_LastName'].str.lower() == last_name.lower())
            ]
            
            if len(voter_data) == 0:
                print(f"No voter found with name {first_name} {last_name}")
                return None
            
            if len(voter_data) > 1:
                print(f"Warning: Multiple voters found with name {first_name} {last_name}, using first one")
            
            # Convert to dictionary
            voter_dict = voter_data.iloc[0].to_dict()
            
            # Clean up the data
            for key, value in voter_dict.items():
                if pd.isna(value):
                    voter_dict[key] = None
                elif isinstance(value, (int, float)) and pd.isna(value):
                    voter_dict[key] = None
            
            return voter_dict
            
        except Exception as e:
            print(f"Error getting voter by name {first_name} {last_name}: {e}")
            return None
    
    def get_all_voters(self) -> List[Dict[str, Any]]:
        """
        Get all voter data.
        
        Returns:
            List[Dict[str, Any]]: List of all voter data dictionaries
        """
        if self.data is None:
            return []
        
        try:
            # Convert all data to list of dictionaries
            voters_list = []
            for _, row in self.data.iterrows():
                voter_dict = row.to_dict()
                
                # Clean up the data
                for key, value in voter_dict.items():
                    if pd.isna(value):
                        voter_dict[key] = None
                    elif isinstance(value, (int, float)) and pd.isna(value):
                        voter_dict[key] = None
                
                voters_list.append(voter_dict)
            
            return voters_list
            
        except Exception as e:
            print(f"Error getting all voters: {e}")
            return []
    
    def get_voter_count(self) -> int:
        """
        Get the total number of voters in the dataset.
        
        Returns:
            int: Total number of voters
        """
        return len(self.data) if self.data is not None else 0
    
    def get_column_names(self) -> List[str]:
        """
        Get all column names from the dataset.
        
        Returns:
            List[str]: List of column names
        """
        return list(self.data.columns) if self.data is not None else []
    
    def get_sample_voter(self) -> Optional[Dict[str, Any]]:
        """
        Get a sample voter from the dataset.
        
        Returns:
            Dict[str, Any]: Sample voter data dictionary or None if no data
        """
        if self.data is None or len(self.data) == 0:
            return None
        
        try:
            # Get first voter
            sample_voter = self.data.iloc[0].to_dict()
            
            # Clean up the data
            for key, value in sample_voter.items():
                if pd.isna(value):
                    sample_voter[key] = None
                elif isinstance(value, (int, float)) and pd.isna(value):
                    sample_voter[key] = None
            
            return sample_voter
            
        except Exception as e:
            print(f"Error getting sample voter: {e}")
            return None
    
    def search_voters(self, search_term: str, column: str = None) -> List[Dict[str, Any]]:
        """
        Search for voters by a search term in a specific column or all columns.
        
        Args:
            search_term (str): Term to search for
            column (str, optional): Specific column to search in. If None, searches all columns.
            
        Returns:
            List[Dict[str, Any]]: List of matching voter data dictionaries
        """
        if self.data is None:
            return []
        
        try:
            if column and column not in self.data.columns:
                print(f"Warning: Column '{column}' not found in dataset")
                return []
            
            if column:
                # Search in specific column
                matching_data = self.data[
                    self.data[column].astype(str).str.contains(search_term, case=False, na=False)
                ]
            else:
                # Search in all columns
                mask = pd.DataFrame([self.data[col].astype(str).str.contains(search_term, case=False, na=False) 
                                   for col in self.data.columns]).any()
                matching_data = self.data[mask]
            
            if len(matching_data) == 0:
                print(f"No voters found matching '{search_term}'")
                return []
            
            # Convert to list of dictionaries
            voters_list = []
            for _, row in matching_data.iterrows():
                voter_dict = row.to_dict()
                
                # Clean up the data
                for key, value in voter_dict.items():
                    if pd.isna(value):
                        voter_dict[key] = None
                    elif isinstance(value, (int, float)) and pd.isna(value):
                        voter_dict[key] = None
                
                voters_list.append(voter_dict)
            
            print(f"Found {len(voters_list)} voters matching '{search_term}'")
            return voters_list
            
        except Exception as e:
            print(f"Error searching voters: {e}")
            return []

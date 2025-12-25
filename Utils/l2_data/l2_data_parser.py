#!/usr/bin/env python3
"""
L2 Data Parser Module
Parses raw L2 data into structured L2DataRow objects.
"""

import pandas as pd
from typing import Dict, Any, Optional, List
from .l2_data_objects import L2DataRow

class L2DataParser:
    """
    Parser for converting raw L2 data into structured L2DataRow objects.
    """
    
    @staticmethod
    def parse_row(data: Dict[str, Any]) -> L2DataRow:
        """
        Parse a single row of raw L2 data into an L2DataRow object.
        
        Args:
            data (Dict[str, Any]): Raw L2 data dictionary
            
        Returns:
            L2DataRow: Parsed and structured L2 data row
        """
        return L2DataRow(data)
    
    @staticmethod
    def parse_csv_file(file_path: str) -> List[L2DataRow]:
        """
        Parse an entire CSV file into a list of L2DataRow objects.
        
        Args:
            file_path (str): Path to the CSV file
            
        Returns:
            List[L2DataRow]: List of parsed L2DataRow objects
        """
        try:
            # Load CSV data with tab delimiter and handle encoding issues
            df = pd.read_csv(file_path, sep='\t', encoding='latin-1', low_memory=False)
            
            # Print column info for debugging
            print(f"Loaded CSV with {len(df.columns)} columns and {len(df)} rows")
            print(f"First few columns: {list(df.columns[:10])}")
            
            # Parse each row
            l2_data_rows = []
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                l2_data_row = L2DataParser.parse_row(row_dict)
                l2_data_rows.append(l2_data_row)
            
            print(f"Parsed {len(l2_data_rows)} rows from {file_path}")
            return l2_data_rows
            
        except Exception as e:
            print(f"Error parsing CSV file {file_path}: {e}")
            return []
    
    @staticmethod
    def parse_dataframe(df: pd.DataFrame) -> List[L2DataRow]:
        """
        Parse a pandas DataFrame into a list of L2DataRow objects.
        
        Args:
            df (pd.DataFrame): Pandas DataFrame containing L2 data
            
        Returns:
            List[L2DataRow]: List of parsed L2DataRow objects
        """
        try:
            l2_data_rows = []
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                l2_data_row = L2DataParser.parse_row(row_dict)
                l2_data_rows.append(l2_data_row)
            
            print(f"Parsed {len(l2_data_rows)} rows from DataFrame")
            return l2_data_rows
            
        except Exception as e:
            print(f"Error parsing DataFrame: {e}")
            return []
    
    @staticmethod
    def create_from_db_record(db_record: Dict[str, Any]) -> L2DataRow:
        """
        Create an L2DataRow object from a database record.
        
        Args:
            db_record (Dict[str, Any]): Database record with agent data
            
        Returns:
            L2DataRow: Parsed and structured L2 data row
        """
        # Convert database record to L2 data format
        l2_data = {
            'SEQUENCE': db_record.get('id', ''),
            'LALVOTERID': f"DB_{db_record.get('id', '')}",
            'Voters_FirstName': db_record.get('name', '').split()[0] if db_record.get('name') else '',
            'Voters_LastName': db_record.get('name', '').split()[-1] if db_record.get('name') else '',
            'Voters_Age': db_record.get('age', 35),
            'Voters_Gender': 'F' if db_record.get('age', 35) > 40 else 'M',  # Simple heuristic
            'ConsumerData_Education_of_Person': db_record.get('education', 'high_school'),
            'ConsumerData_Estimated_Income_Amount': db_record.get('estimated_income', 50000),
            'ConsumerData_Number_Of_Persons_in_HH': db_record.get('household_size', 2),
            'shopping_preferences': db_record.get('shopping_preferences', {})
        }
        
        return L2DataRow(l2_data)
    
    @staticmethod
    def validate_data(data: Dict[str, Any]) -> bool:
        """
        Validate that the data contains required fields for L2 data.
        
        Args:
            data (Dict[str, Any]): Data dictionary to validate
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        required_fields = ['SEQUENCE', 'LALVOTERID']
        optional_fields = ['Voters_FirstName', 'Voters_LastName', 'Voters_Age', 'Voters_Gender']
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                print(f"Missing required field: {field}")
                return False
        
        # Check if at least one optional field is present
        has_optional_fields = any(field in data for field in optional_fields)
        if not has_optional_fields:
            print("No optional fields found - data may be incomplete")
            return False
        
        return True
    
    @staticmethod
    def clean_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and normalize the data dictionary.
        
        Args:
            data (Dict[str, Any]): Raw data dictionary
            
        Returns:
            Dict[str, Any]: Cleaned data dictionary
        """
        cleaned_data = {}
        
        for key, value in data.items():
            # Handle NaN values
            if pd.isna(value):
                cleaned_data[key] = None
            # Handle empty strings
            elif isinstance(value, str) and value.strip() == '':
                cleaned_data[key] = None
            # Handle numeric values
            elif isinstance(value, (int, float)):
                if pd.isna(value):
                    cleaned_data[key] = None
                else:
                    cleaned_data[key] = value
            # Handle other types
            else:
                cleaned_data[key] = value
        
        return cleaned_data
    
    @staticmethod
    def extract_key_fields(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract key fields from the data for quick access.
        
        Args:
            data (Dict[str, Any]): Raw data dictionary
            
        Returns:
            Dict[str, Any]: Dictionary with key fields only
        """
        key_fields = [
            'SEQUENCE', 'LALVOTERID',
            'Voters_FirstName', 'Voters_MiddleName', 'Voters_LastName', 'Voters_NameSuffix',
            'Voters_Age', 'Voters_Gender', 'Voters_BirthDate', 'Voters_Ethnicity',
            'Voters_Party', 'Voters_RegDate', 'Voters_Active',
            'Residence_Addresses_AddressLine', 'Residence_Addresses_City', 
            'Residence_Addresses_State', 'Residence_Addresses_ZipCode',
            'Residence_Addresses_County', 'Residence_Addresses_CongressionalDistrict'
        ]
        
        return {field: data.get(field, None) for field in key_fields}
    
    @staticmethod
    def get_data_summary(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of the data contents.
        
        Args:
            data (Dict[str, Any]): Data dictionary
            
        Returns:
            Dict[str, Any]: Summary dictionary
        """
        summary = {
            'total_fields': len(data),
            'non_null_fields': sum(1 for v in data.values() if v is not None and not pd.isna(v)),
            'null_fields': sum(1 for v in data.values() if v is None or pd.isna(v)),
            'field_types': {}
        }
        
        # Count field types
        for key, value in data.items():
            if value is None or pd.isna(value):
                field_type = 'null'
            else:
                field_type = type(value).__name__
            
            summary['field_types'][field_type] = summary['field_types'].get(field_type, 0) + 1
        
        return summary
    
    @staticmethod
    def convert_to_legacy_format(l2_data_row: L2DataRow) -> Dict[str, Any]:
        """
        Convert an L2DataRow object back to the legacy format for compatibility.
        
        Args:
            l2_data_row (L2DataRow): Structured L2 data row
            
        Returns:
            Dict[str, Any]: Legacy format data dictionary
        """
        return l2_data_row.all_data()
    
    @staticmethod
    def merge_data_rows(rows: List[L2DataRow]) -> pd.DataFrame:
        """
        Merge multiple L2DataRow objects into a pandas DataFrame.
        
        Args:
            rows (List[L2DataRow]): List of L2DataRow objects
            
        Returns:
            pd.DataFrame: Merged DataFrame
        """
        if not rows:
            return pd.DataFrame()
        
        # Convert each row to dictionary and collect
        data_dicts = []
        for row in rows:
            data_dicts.append(row.all_data())
        
        # Create DataFrame
        df = pd.DataFrame(data_dicts)
        return df
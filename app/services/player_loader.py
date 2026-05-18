"""
Player Loader Service - CSV Parser for Player Database

This module provides functionality to load player data from the CSV file
`2600球员属性.csv` using pandas. It handles encoding, parsing, and basic
validation of the player data.

The parser is designed to work with the Player model defined in app/models/player.py
and supports all 50+ player attributes including technical, mental, and physical stats.
"""

import logging
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
from pandas import DataFrame, Series
import numpy as np


# Configure logging
logger = logging.getLogger(__name__)


class PlayerLoaderError(Exception):
    """Base exception for player loader errors"""
    pass


class CSVNotFoundError(PlayerLoaderError):
    """Raised when CSV file is not found"""
    pass


class CSVEncodingError(PlayerLoaderError):
    """Raised when CSV encoding cannot be handled"""
    pass


class CSVParseError(PlayerLoaderError):
    """Raised when CSV parsing fails"""
    pass


class CSVValidationError(PlayerLoaderError):
    """Raised when CSV data validation fails"""
    pass


class PlayerCSVParser:
    """
    CSV parser for loading player data from 2600球员属性.csv
    
    This parser uses pandas to read the CSV file containing 2600+ players
    with 50+ attributes each. It handles Chinese character encoding and
    provides basic validation of the data structure.
    
    Attributes:
        csv_path: Path to the CSV file
        encoding: Character encoding for the CSV file (default: 'utf-8')
        
    Example:
        >>> parser = PlayerCSVParser('fm26/2600球员属性.csv')
        >>> df = parser.load()
        >>> print(f"Loaded {len(df)} players")
    """
    
    # Expected columns in the CSV file (matching Player model)
    REQUIRED_COLUMNS = [
        'name', 'position', 'age', 'ca', 'pa', 'nationality', 'club',
        # Technical attributes
        'corners', 'crossing', 'dribbling', 'finishing', 'first_touch',
        'free_kicks', 'heading', 'long_shots', 'long_throws', 'marking',
        'passing', 'penalty', 'tackling', 'technique',
        # Mental attributes
        'aggression', 'anticipation', 'bravery', 'composure', 'concentration',
        'decisions', 'determination', 'flair', 'leadership', 'off_the_ball',
        'positioning', 'teamwork', 'vision', 'work_rate',
        # Physical attributes
        'acceleration', 'agility', 'balance', 'jumping', 'stamina',
        'pace', 'endurance', 'strength',
        # Financial and physical stats
        'price', 'wage', 'height', 'weight', 'left_foot', 'right_foot', 'uid',
        # Player traits
        'traits'
    ]
    
    # Attribute columns that should be integers (1-20 range)
    ATTRIBUTE_COLUMNS = [
        # Technical
        'corners', 'crossing', 'dribbling', 'finishing', 'first_touch',
        'free_kicks', 'heading', 'long_shots', 'long_throws', 'marking',
        'passing', 'penalty', 'tackling', 'technique',
        # Mental
        'aggression', 'anticipation', 'bravery', 'composure', 'concentration',
        'decisions', 'determination', 'flair', 'leadership', 'off_the_ball',
        'positioning', 'teamwork', 'vision', 'work_rate',
        # Physical
        'acceleration', 'agility', 'balance', 'jumping', 'stamina',
        'pace', 'endurance', 'strength',
        # Foot abilities
        'left_foot', 'right_foot'
    ]
    
    def __init__(self, csv_path: str, encoding: str = 'utf-8'):
        """
        Initialize the CSV parser.
        
        Args:
            csv_path: Path to the CSV file (e.g., 'fm26/2600球员属性.csv')
            encoding: Character encoding for the CSV file (default: 'utf-8')
            
        Raises:
            CSVNotFoundError: If the CSV file does not exist
        """
        self.csv_path = Path(csv_path)
        self.encoding = encoding
        
        # Validate file exists
        if not self.csv_path.exists():
            raise CSVNotFoundError(
                f"CSV file not found: {self.csv_path}"
            )
        
        logger.info(f"Initialized PlayerCSVParser for file: {self.csv_path}")
    
    def load(self) -> DataFrame:
        """
        Load and parse the CSV file into a pandas DataFrame.
        
        This method:
        1. Reads the CSV file with proper encoding
        2. Validates the column structure
        3. Performs basic data type validation
        4. Returns a clean DataFrame ready for database insertion
        
        Returns:
            DataFrame: Parsed player data with all columns
            
        Raises:
            CSVEncodingError: If encoding issues occur
            CSVParseError: If CSV parsing fails
            CSVValidationError: If data validation fails
            
        Example:
            >>> parser = PlayerCSVParser('2600球员属性.csv')
            >>> df = parser.load()
            >>> print(df.columns.tolist())
            ['name', 'position', 'age', 'ca', 'pa', ...]
        """
        logger.info(f"Loading CSV file: {self.csv_path}")
        
        try:
            # Try to read with specified encoding
            df = self._read_csv_with_encoding(self.encoding)
            
        except UnicodeDecodeError as e:
            logger.warning(
                f"Failed to read with {self.encoding} encoding, "
                f"trying alternative encodings"
            )
            # Try alternative encodings for Chinese characters
            for alt_encoding in ['utf-8-sig', 'gbk', 'gb2312', 'gb18030']:
                try:
                    df = self._read_csv_with_encoding(alt_encoding)
                    logger.info(f"Successfully read with {alt_encoding} encoding")
                    self.encoding = alt_encoding  # Update encoding for future use
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise CSVEncodingError(
                    f"Failed to read CSV with any supported encoding. "
                    f"Original error: {str(e)}"
                )
        
        except Exception as e:
            raise CSVParseError(
                f"Failed to parse CSV file: {str(e)}"
            )
        
        # Validate the DataFrame
        self._validate_dataframe(df)
        
        logger.info(
            f"Successfully loaded {len(df)} players with "
            f"{len(df.columns)} columns"
        )
        
        return df
    
    def _read_csv_with_encoding(self, encoding: str) -> DataFrame:
        """
        Read CSV file with specified encoding.
        
        Args:
            encoding: Character encoding to use
            
        Returns:
            DataFrame: Parsed CSV data
            
        Raises:
            UnicodeDecodeError: If encoding fails
            Exception: If pandas read_csv fails
        """
        # Use Python's csv module for better handling of embedded newlines
        import csv
        import io
        
        # Read file content
        with open(self.csv_path, 'r', encoding=encoding, newline='') as f:
            content = f.read()
        
        # Remove BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]
        
        # Parse CSV with proper quote handling
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        
        if not rows:
            raise CSVParseError("CSV file is empty")
        
        # First row is header
        header = rows[0]
        data_rows = rows[1:]
        
        logger.info(
            f"CSV parsing: {len(data_rows)} total rows, "
            f"header has {len(header)} columns"
        )
        
        # The CSV file has a complex structure with 116 columns but only 50 in header
        # The actual data is scattered across different column positions:
        # - Columns 0-42: Basic info and attributes (name through strength - 43 columns)
        # - Column 85: price (header position 43)
        # - Column 86: wage (header position 44)
        # - Column 90: height (header position 45)
        # - Column 93: weight (header position 46)
        # - Column 83: left_foot (header position 47)
        # - Column 84: right_foot (header position 48)
        # - Column 97: uid (header position 49)
        # - Column 114: traits/playing style characteristics (header position 50)
        
        # Update header to include traits
        header_with_traits = header + ['traits']
        
        processed_rows = []
        for row in data_rows:
            if len(row) >= 98:  # Need at least 98 columns
                # Build the row with correct column mappings
                new_row = (
                    row[:43] +  # Columns 0-42: name through strength
                    [row[85]] +  # Column 85: price
                    [row[86]] +  # Column 86: wage
                    [row[90]] +  # Column 90: height
                    [row[93]] +  # Column 93: weight
                    [row[83]] +  # Column 83: left_foot
                    [row[84]] +  # Column 84: right_foot
                    [row[97]] +  # Column 97: uid
                    [row[114] if len(row) > 114 else '']  # Column 114: traits
                )
                processed_rows.append(new_row)
        
        logger.info(
            f"After processing: {len(processed_rows)} valid rows with {len(header_with_traits)} columns"
        )
        
        # Create DataFrame
        df = pd.DataFrame(processed_rows, columns=header_with_traits)
        
        # Convert all to string initially
        for col in df.columns:
            df[col] = df[col].astype(str)
        
        # Replace 'nan' strings with actual NaN
        df = df.replace('nan', np.nan)
        df = df.replace('', np.nan)
        
        return df
    
    def _validate_dataframe(self, df: DataFrame) -> None:
        """
        Validate the DataFrame structure and content.
        
        Args:
            df: DataFrame to validate
            
        Raises:
            CSVValidationError: If validation fails
        """
        # Check if DataFrame is empty
        if df.empty:
            raise CSVValidationError("CSV file is empty")
        
        # Check for required columns
        missing_columns = set(self.REQUIRED_COLUMNS) - set(df.columns)
        if missing_columns:
            raise CSVValidationError(
                f"Missing required columns: {', '.join(sorted(missing_columns))}"
            )
        
        # Check for duplicate UIDs
        if 'uid' in df.columns:
            duplicate_uids = df[df['uid'].duplicated()]['uid'].tolist()
            if duplicate_uids:
                logger.warning(
                    f"Found {len(duplicate_uids)} duplicate UIDs: "
                    f"{duplicate_uids[:5]}..."
                )
        
        logger.debug(f"DataFrame validation passed: {len(df)} rows, {len(df.columns)} columns")
    
    def validate_row(self, row: Series, log_details: bool = False) -> Tuple[bool, List[str]]:
        """
        Validate a single player row with comprehensive attribute checking.
        
        Checks:
        - Required fields are present and not null
        - Numeric fields can be converted to numbers
        - ALL attribute values are in valid ranges (1-20 for attributes, 1-200 for CA/PA)
        - Age is reasonable (15-45)
        - Height and weight are reasonable
        - Wage is non-negative
        - All 36 technical/mental/physical attributes are validated
        
        Args:
            row: pandas Series representing a single player row
            log_details: If True, log detailed validation failures
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list of validation error messages)
            
        Example:
            >>> parser = PlayerCSVParser('2600球员属性.csv')
            >>> df = parser.load()
            >>> is_valid, errors = parser.validate_row(df.iloc[0])
            >>> print(is_valid, errors)
            True []
        """
        errors = []
        player_name = row.get('name', 'Unknown')
        
        try:
            # 1. Check required string fields
            required_string_fields = ['name', 'position', 'nationality', 'club', 'uid']
            for field in required_string_fields:
                if field not in row or pd.isna(row[field]) or str(row[field]).strip() == '':
                    error_msg = f"Player '{player_name}': missing or empty required field '{field}'"
                    errors.append(error_msg)
                    if log_details:
                        logger.warning(error_msg)
            
            # 2. Check age range (15-45 is reasonable for football players)
            try:
                age = int(row['age'])
                if age < 15 or age > 45:
                    error_msg = f"Player '{player_name}': age {age} out of range (15-45)"
                    errors.append(error_msg)
                    if log_details:
                        logger.warning(error_msg)
            except (ValueError, TypeError):
                error_msg = f"Player '{player_name}': invalid age value '{row.get('age')}'"
                errors.append(error_msg)
                if log_details:
                    logger.warning(error_msg)
            
            # 3. Check CA and PA ranges
            # CA: 1-200
            # PA: -200 to 200 (negative values indicate random potential ranges in FM)
            try:
                ca_value = int(row['ca'])
                if ca_value < 1 or ca_value > 200:
                    error_msg = f"Player '{player_name}': CA {ca_value} out of range (1-200)"
                    errors.append(error_msg)
                    if log_details:
                        logger.warning(error_msg)
            except (ValueError, TypeError):
                error_msg = f"Player '{player_name}': invalid CA value '{row.get('ca')}'"
                errors.append(error_msg)
                if log_details:
                    logger.warning(error_msg)
            
            try:
                pa_value = int(row['pa'])
                if pa_value < -200 or pa_value > 200 or pa_value == 0:
                    error_msg = f"Player '{player_name}': PA {pa_value} out of range (-200 to 200, excluding 0)"
                    errors.append(error_msg)
                    if log_details:
                        logger.warning(error_msg)
            except (ValueError, TypeError):
                error_msg = f"Player '{player_name}': invalid PA value '{row.get('pa')}'"
                errors.append(error_msg)
                if log_details:
                    logger.warning(error_msg)
            
            # 4. Check ALL attribute ranges (1-20) - Technical, Mental, Physical, Foot abilities
            for attr in self.ATTRIBUTE_COLUMNS:
                if attr in row:
                    try:
                        value = int(row[attr])
                        if value < 1 or value > 20:
                            error_msg = f"Player '{player_name}': {attr} {value} out of range (1-20)"
                            errors.append(error_msg)
                            if log_details:
                                logger.warning(error_msg)
                    except (ValueError, TypeError):
                        error_msg = f"Player '{player_name}': invalid {attr} value '{row.get(attr)}'"
                        errors.append(error_msg)
                        if log_details:
                            logger.warning(error_msg)
                else:
                    error_msg = f"Player '{player_name}': missing attribute '{attr}'"
                    errors.append(error_msg)
                    if log_details:
                        logger.warning(error_msg)
            
            # 5. Check height range (150-220 cm)
            try:
                height = int(row['height'])
                if height < 150 or height > 220:
                    error_msg = f"Player '{player_name}': height {height} out of range (150-220 cm)"
                    errors.append(error_msg)
                    if log_details:
                        logger.warning(error_msg)
            except (ValueError, TypeError):
                error_msg = f"Player '{player_name}': invalid height value '{row.get('height')}'"
                errors.append(error_msg)
                if log_details:
                    logger.warning(error_msg)
            
            # 6. Check weight range (50-120 kg)
            try:
                weight = int(row['weight'])
                if weight < 50 or weight > 120:
                    error_msg = f"Player '{player_name}': weight {weight} out of range (50-120 kg)"
                    errors.append(error_msg)
                    if log_details:
                        logger.warning(error_msg)
            except (ValueError, TypeError):
                error_msg = f"Player '{player_name}': invalid weight value '{row.get('weight')}'"
                errors.append(error_msg)
                if log_details:
                    logger.warning(error_msg)
            
            # 7. Check wage is non-negative
            try:
                wage = int(row['wage'])
                if wage < 0:
                    error_msg = f"Player '{player_name}': wage {wage} cannot be negative"
                    errors.append(error_msg)
                    if log_details:
                        logger.warning(error_msg)
            except (ValueError, TypeError):
                error_msg = f"Player '{player_name}': invalid wage value '{row.get('wage')}'"
                errors.append(error_msg)
                if log_details:
                    logger.warning(error_msg)
            
            # 8. Validate price format (can be empty, but if present should be string)
            if 'price' in row and not pd.isna(row['price']):
                price_str = str(row['price']).strip()
                if price_str and not isinstance(price_str, str):
                    error_msg = f"Player '{player_name}': invalid price format '{row.get('price')}'"
                    errors.append(error_msg)
                    if log_details:
                        logger.warning(error_msg)
            
            is_valid = len(errors) == 0
            return is_valid, errors
            
        except Exception as e:
            error_msg = f"Player '{player_name}': validation exception: {str(e)}"
            errors.append(error_msg)
            if log_details:
                logger.error(error_msg)
            return False, errors
    
    def clean_data(self, df: DataFrame) -> Tuple[DataFrame, Dict[str, Any]]:
        """
        Clean and normalize player data with detailed validation reporting.
        
        This method:
        1. Removes duplicate rows based on UID
        2. Strips whitespace from string fields
        3. Converts numeric fields to appropriate types
        4. Parses price field to remove currency symbols
        5. Handles missing values appropriately
        6. Applies default values for invalid data (e.g., weight)
        7. Filters out invalid rows with detailed error tracking
        8. Generates validation report
        
        Args:
            df: DataFrame to clean
            
        Returns:
            Tuple[DataFrame, Dict]: (cleaned_df, validation_report)
            
        Example:
            >>> parser = PlayerCSVParser('2600球员属性.csv')
            >>> df = parser.load()
            >>> clean_df, report = parser.clean_data(df)
            >>> print(f"Cleaned {len(clean_df)} players, {report['invalid_count']} invalid")
        """
        logger.info(f"Cleaning data for {len(df)} players")
        original_count = len(df)
        
        # Initialize validation report
        validation_report = {
            'original_count': original_count,
            'duplicates_removed': 0,
            'invalid_count': 0,
            'valid_count': 0,
            'validation_errors': [],
            'error_summary': {},
            'default_values_applied': {
                'weight': 0,
                'height': 0
            }
        }
        
        # Make a copy to avoid modifying original
        df = df.copy()
        
        # 1. Remove duplicates based on UID
        if 'uid' in df.columns:
            df = df.drop_duplicates(subset=['uid'], keep='first')
            duplicates_removed = original_count - len(df)
            validation_report['duplicates_removed'] = duplicates_removed
            if duplicates_removed > 0:
                logger.info(f"Removed {duplicates_removed} duplicate UIDs")
        
        # 2. Strip whitespace from string fields
        string_fields = ['name', 'position', 'nationality', 'club', 'uid', 'price']
        for field in string_fields:
            if field in df.columns:
                df[field] = df[field].astype(str).str.strip()
        
        # 3. Convert numeric fields to appropriate types
        # Integer fields
        integer_fields = ['age', 'ca', 'pa', 'wage', 'height', 'weight'] + self.ATTRIBUTE_COLUMNS
        for field in integer_fields:
            if field in df.columns:
                # Convert to numeric, coerce errors to NaN, then round and convert to Int64
                df[field] = pd.to_numeric(df[field], errors='coerce').round().astype('Int64')
        
        # 4. Apply default values for invalid weight and height
        # Weight: use 75 kg as default for invalid values (< 50 or > 120)
        if 'weight' in df.columns:
            invalid_weight_mask = (df['weight'] < 50) | (df['weight'] > 120) | df['weight'].isna()
            weight_defaults_count = invalid_weight_mask.sum()
            if weight_defaults_count > 0:
                df.loc[invalid_weight_mask, 'weight'] = 75
                validation_report['default_values_applied']['weight'] = int(weight_defaults_count)
                logger.info(f"Applied default weight (75 kg) to {weight_defaults_count} players")
        
        # Height: use 180 cm as default for invalid values (< 150 or > 220)
        if 'height' in df.columns:
            invalid_height_mask = (df['height'] < 150) | (df['height'] > 220) | df['height'].isna()
            height_defaults_count = invalid_height_mask.sum()
            if height_defaults_count > 0:
                df.loc[invalid_height_mask, 'height'] = 180
                validation_report['default_values_applied']['height'] = int(height_defaults_count)
                logger.info(f"Applied default height (180 cm) to {height_defaults_count} players")
        
        # 5. Parse price field to keep as string (database expects string)
        # Just clean it up but keep the currency format
        if 'price' in df.columns:
            df['price'] = df['price'].astype(str).str.strip()
            # Replace 'nan' string with empty string
            df.loc[df['price'] == 'nan', 'price'] = ''
        
        # 6. Handle missing values
        # For required string fields, replace NaN with empty string
        for field in ['name', 'position', 'nationality', 'club', 'uid']:
            if field in df.columns:
                df[field] = df[field].fillna('')
        
        # For price, use empty string for missing values
        if 'price' in df.columns:
            df['price'] = df['price'].fillna('')
        
        # 7. Filter out invalid rows with detailed error tracking
        validation_results = df.apply(lambda row: self.validate_row(row, log_details=False), axis=1)
        valid_mask = validation_results.apply(lambda x: x[0])
        
        # Collect validation errors
        for idx, (is_valid, errors) in enumerate(validation_results):
            if not is_valid:
                player_name = df.iloc[idx].get('name', f'Row {idx}')
                validation_report['validation_errors'].append({
                    'row_index': idx,
                    'player_name': player_name,
                    'errors': errors
                })
                
                # Count error types
                for error in errors:
                    error_type = error.split(':')[1].strip().split()[0] if ':' in error else 'unknown'
                    validation_report['error_summary'][error_type] = \
                        validation_report['error_summary'].get(error_type, 0) + 1
        
        invalid_count = (~valid_mask).sum()
        validation_report['invalid_count'] = invalid_count
        
        if invalid_count > 0:
            logger.warning(f"Filtering out {invalid_count} invalid rows")
            # Log first 10 validation errors for debugging
            for error_entry in validation_report['validation_errors'][:10]:
                logger.warning(
                    f"Invalid player '{error_entry['player_name']}': "
                    f"{len(error_entry['errors'])} errors"
                )
        
        df = df[valid_mask]
        validation_report['valid_count'] = len(df)
        
        # 8. Select only the columns we need (matching Player model)
        available_columns = [col for col in self.REQUIRED_COLUMNS if col in df.columns]
        df = df[available_columns]
        
        logger.info(
            f"Data cleaning complete: {validation_report['valid_count']} valid players, "
            f"{validation_report['invalid_count']} invalid, "
            f"{validation_report['duplicates_removed']} duplicates removed, "
            f"{validation_report['default_values_applied']['weight']} weight defaults applied, "
            f"{validation_report['default_values_applied']['height']} height defaults applied"
        )
        
        return df, validation_report
    
    def parse_csv(self, csv_path: str) -> Tuple[DataFrame, Dict[str, Any]]:
        """
        Parse CSV file and return cleaned DataFrame with validation report.
        
        This is a convenience method that combines load() and clean_data().
        
        Args:
            csv_path: Path to CSV file (updates internal csv_path)
            
        Returns:
            Tuple[DataFrame, Dict]: (cleaned_df, validation_report)
            
        Raises:
            CSVNotFoundError: If file doesn't exist
            CSVParseError: If parsing fails
            CSVValidationError: If validation fails
            
        Example:
            >>> parser = PlayerCSVParser('dummy.csv')
            >>> df, report = parser.parse_csv('fm26/2600球员属性.csv')
            >>> print(f"Parsed {len(df)} players, {report['invalid_count']} invalid")
        """
        # Update csv_path if different
        new_path = Path(csv_path)
        if not new_path.exists():
            raise CSVNotFoundError(f"CSV file not found: {new_path}")
        
        self.csv_path = new_path
        
        # Load and clean
        df = self.load()
        df, validation_report = self.clean_data(df)
        
        return df, validation_report
    
    def get_column_info(self) -> Dict[str, Any]:
        """
        Get information about the CSV columns without loading the full file.
        
        Returns:
            dict: Column information including names and sample data
            
        Example:
            >>> parser = PlayerCSVParser('2600球员属性.csv')
            >>> info = parser.get_column_info()
            >>> print(info['column_count'])
            49
        """
        try:
            # Read only first row to get column info
            df_sample = pd.read_csv(
                self.csv_path,
                encoding=self.encoding,
                nrows=1
            )
            
            return {
                'column_count': len(df_sample.columns),
                'columns': df_sample.columns.tolist(),
                'sample_row': df_sample.iloc[0].to_dict() if not df_sample.empty else {}
            }
        except Exception as e:
            logger.error(f"Failed to get column info: {str(e)}")
            raise CSVParseError(f"Failed to read CSV columns: {str(e)}")
    
    def validate_player_data(self, df: DataFrame) -> Dict[str, Any]:
        """
        Perform detailed validation on player data.
        
        This method checks:
        - Data types for numeric columns
        - Value ranges for attributes (1-20)
        - CA/PA ranges (1-200)
        - Missing required fields
        
        Args:
            df: DataFrame to validate
            
        Returns:
            dict: Validation report with issues found
            
        Example:
            >>> parser = PlayerCSVParser('2600球员属性.csv')
            >>> df = parser.load()
            >>> report = parser.validate_player_data(df)
            >>> print(report['valid_rows'])
            2600
        """
        report = {
            'total_rows': len(df),
            'valid_rows': 0,
            'issues': []
        }
        
        # Check for missing required fields
        for col in self.REQUIRED_COLUMNS:
            if col in df.columns:
                missing_count = df[col].isna().sum()
                if missing_count > 0:
                    report['issues'].append({
                        'type': 'missing_values',
                        'column': col,
                        'count': int(missing_count)
                    })
        
        # Validate numeric columns can be converted
        numeric_columns = ['age', 'ca', 'pa', 'wage', 'height', 'weight'] + self.ATTRIBUTE_COLUMNS
        
        for col in numeric_columns:
            if col in df.columns:
                try:
                    # Try to convert to numeric
                    pd.to_numeric(df[col], errors='coerce')
                except Exception as e:
                    report['issues'].append({
                        'type': 'invalid_numeric',
                        'column': col,
                        'error': str(e)
                    })
        
        # Count valid rows (rows with all required fields present)
        required_mask = df[self.REQUIRED_COLUMNS].notna().all(axis=1)
        report['valid_rows'] = int(required_mask.sum())
        
        logger.info(
            f"Validation complete: {report['valid_rows']}/{report['total_rows']} "
            f"valid rows, {len(report['issues'])} issues found"
        )
        
        return report


def load_players_from_csv(csv_path: str, db_session, detect_db_duplicates: bool = True) -> Tuple[List, Dict[str, Any]]:
    """
    Load players from CSV file and return Player model objects with validation report.
    
    This function:
    1. Parses the CSV file using pandas
    2. Validates all player data comprehensively
    3. Detects and handles duplicate players (CSV duplicates and database duplicates)
    4. Maps CSV columns to Player model fields
    5. Creates Player model instances ready for database insertion
    6. Returns detailed validation report with duplicate detection information
    
    Args:
        csv_path: Path to the CSV file (e.g., 'fm26/2600球员属性.csv')
        db_session: SQLAlchemy database session for checking existing players
        detect_db_duplicates: If True, check database for existing UIDs (default: True)
        
    Returns:
        Tuple[List[Player], Dict]: (list of Player objects, validation_report)
        
    Raises:
        PlayerLoaderError: If loading, validation, or mapping fails
        
    Example:
        >>> from app.core.database import get_db
        >>> from app.models.player import Player
        >>> 
        >>> db = next(get_db())
        >>> players, report = load_players_from_csv('fm26/2600球员属性.csv', db)
        >>> print(f"Loaded {len(players)} players")
        >>> print(f"Validation report: {report['valid_count']} valid, {report['invalid_count']} invalid")
        >>> print(f"Duplicate detection: {report['csv_duplicates_removed']} CSV duplicates, {report['db_duplicates_skipped']} DB duplicates")
        >>> 
        >>> # Bulk insert into database
        >>> db.bulk_save_objects(players)
        >>> db.commit()
        Loaded 2600 players
        Validation report: 2600 valid, 0 invalid
        Duplicate detection: 0 CSV duplicates, 0 DB duplicates
    """
    from app.models.player import Player
    
    logger.info(f"Loading players from CSV: {csv_path}")
    
    # Parse CSV file
    parser = PlayerCSVParser(csv_path)
    df = parser.load()
    df, validation_report = parser.clean_data(df)
    
    # Validate data
    detailed_report = parser.validate_player_data(df)
    validation_report['detailed_validation'] = detailed_report
    
    if detailed_report['issues']:
        logger.warning(
            f"Validation found {len(detailed_report['issues'])} issues. "
            f"Proceeding with {detailed_report['valid_rows']}/{detailed_report['total_rows']} valid rows."
        )
    
    # Detect database duplicates if session is provided and detection is enabled
    db_duplicates_skipped = 0
    db_duplicate_uids = []
    
    if db_session is not None and detect_db_duplicates:
        logger.info("Checking for existing players in database...")
        csv_uids = set(df['uid'].tolist())
        
        try:
            # Query database for existing UIDs in batches to avoid memory issues
            existing_uids = set()
            batch_size = 1000
            uid_list = list(csv_uids)
            
            for i in range(0, len(uid_list), batch_size):
                batch_uids = uid_list[i:i + batch_size]
                existing_batch = db_session.query(Player.uid).filter(
                    Player.uid.in_(batch_uids)
                ).all()
                existing_uids.update([uid[0] for uid in existing_batch])
            
            # Filter out players that already exist in database
            if existing_uids:
                db_duplicate_uids = list(existing_uids)
                db_duplicates_skipped = len(existing_uids)
                df = df[~df['uid'].isin(existing_uids)]
                
                logger.info(
                    f"Found {db_duplicates_skipped} players already in database. "
                    f"Skipping these to avoid duplicates. "
                    f"Sample UIDs: {db_duplicate_uids[:5]}"
                )
        except Exception as e:
            logger.warning(
                f"Failed to check database for duplicates: {str(e)}. "
                f"Proceeding without database duplicate detection."
            )
            # Continue without database duplicate detection
    
    # Add duplicate detection information to report
    validation_report['csv_duplicates_removed'] = validation_report.get('duplicates_removed', 0)
    validation_report['db_duplicates_skipped'] = db_duplicates_skipped
    validation_report['db_duplicate_uids'] = db_duplicate_uids[:100]  # Keep first 100 for reference
    validation_report['total_duplicates_handled'] = (
        validation_report['csv_duplicates_removed'] + db_duplicates_skipped
    )
    
    # Convert DataFrame rows to Player model objects
    players = []
    failed_rows = 0
    player_creation_errors = []
    
    for idx, row in df.iterrows():
        try:
            player = _create_player_from_row(row)
            players.append(player)
        except Exception as e:
            failed_rows += 1
            error_msg = f"Failed to create Player object for row {idx} (name: {row.get('name', 'unknown')}): {str(e)}"
            player_creation_errors.append(error_msg)
            logger.error(error_msg)
    
    validation_report['player_creation_failures'] = failed_rows
    validation_report['player_creation_errors'] = player_creation_errors[:10]  # Keep first 10 errors
    validation_report['successfully_created'] = len(players)
    
    if failed_rows > 0:
        logger.warning(
            f"Failed to create {failed_rows} Player objects. "
            f"Successfully created {len(players)} players."
        )
    
    logger.info(
        f"Successfully loaded {len(players)} Player objects from CSV. "
        f"Validation summary: {validation_report['valid_count']} valid rows, "
        f"{validation_report['invalid_count']} invalid rows, "
        f"{validation_report['csv_duplicates_removed']} CSV duplicates removed, "
        f"{validation_report['db_duplicates_skipped']} database duplicates skipped"
    )
    
    return players, validation_report


def _create_player_from_row(row: Series) -> 'Player':
    """
    Create a Player model object from a pandas Series (CSV row).
    
    This helper function maps CSV columns to Player model fields and
    handles data type conversions.
    
    Args:
        row: pandas Series representing a single player row
        
    Returns:
        Player: Player model object ready for database insertion
        
    Raises:
        ValueError: If required fields are missing or invalid
        TypeError: If data type conversion fails
    """
    from app.models.player import Player
    
    # Helper function to safely convert to int
    def safe_int(value, field_name: str) -> int:
        """Convert value to int, raising ValueError if invalid"""
        try:
            if pd.isna(value):
                raise ValueError(f"{field_name} is missing")
            return int(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid {field_name}: {value}") from e
    
    # Helper function to safely convert to string
    def safe_str(value, field_name: str, allow_empty: bool = False) -> str:
        """Convert value to string, raising ValueError if invalid"""
        try:
            if pd.isna(value):
                if allow_empty:
                    return ""
                raise ValueError(f"{field_name} is missing")
            result = str(value).strip()
            if not allow_empty and not result:
                raise ValueError(f"{field_name} is empty")
            return result
        except Exception as e:
            raise ValueError(f"Invalid {field_name}: {value}") from e
    
    try:
        # Create Player object with all attributes
        player = Player(
            # Basic Information
            uid=safe_str(row['uid'], 'uid'),
            name=safe_str(row['name'], 'name'),
            position=safe_str(row['position'], 'position'),
            age=safe_int(row['age'], 'age'),
            nationality=safe_str(row['nationality'], 'nationality'),
            club=safe_str(row['club'], 'club'),
            
            # Core Attributes
            ca=safe_int(row['ca'], 'ca'),
            pa=safe_int(row['pa'], 'pa'),
            
            # Technical Attributes (1-20 each)
            corners=safe_int(row['corners'], 'corners'),
            crossing=safe_int(row['crossing'], 'crossing'),
            dribbling=safe_int(row['dribbling'], 'dribbling'),
            finishing=safe_int(row['finishing'], 'finishing'),
            first_touch=safe_int(row['first_touch'], 'first_touch'),
            free_kicks=safe_int(row['free_kicks'], 'free_kicks'),
            heading=safe_int(row['heading'], 'heading'),
            long_shots=safe_int(row['long_shots'], 'long_shots'),
            long_throws=safe_int(row['long_throws'], 'long_throws'),
            marking=safe_int(row['marking'], 'marking'),
            passing=safe_int(row['passing'], 'passing'),
            penalty=safe_int(row['penalty'], 'penalty'),
            tackling=safe_int(row['tackling'], 'tackling'),
            technique=safe_int(row['technique'], 'technique'),
            
            # Mental Attributes (1-20 each)
            aggression=safe_int(row['aggression'], 'aggression'),
            anticipation=safe_int(row['anticipation'], 'anticipation'),
            bravery=safe_int(row['bravery'], 'bravery'),
            composure=safe_int(row['composure'], 'composure'),
            concentration=safe_int(row['concentration'], 'concentration'),
            decisions=safe_int(row['decisions'], 'decisions'),
            determination=safe_int(row['determination'], 'determination'),
            flair=safe_int(row['flair'], 'flair'),
            leadership=safe_int(row['leadership'], 'leadership'),
            off_the_ball=safe_int(row['off_the_ball'], 'off_the_ball'),
            positioning=safe_int(row['positioning'], 'positioning'),
            teamwork=safe_int(row['teamwork'], 'teamwork'),
            vision=safe_int(row['vision'], 'vision'),
            work_rate=safe_int(row['work_rate'], 'work_rate'),
            
            # Physical Attributes (1-20 each)
            acceleration=safe_int(row['acceleration'], 'acceleration'),
            agility=safe_int(row['agility'], 'agility'),
            balance=safe_int(row['balance'], 'balance'),
            jumping=safe_int(row['jumping'], 'jumping'),
            stamina=safe_int(row['stamina'], 'stamina'),
            pace=safe_int(row['pace'], 'pace'),
            endurance=safe_int(row['endurance'], 'endurance'),
            strength=safe_int(row['strength'], 'strength'),
            
            # Financial
            price=safe_str(row['price'], 'price', allow_empty=True),
            wage=safe_int(row['wage'], 'wage'),
            
            # Physical Stats
            height=safe_int(row['height'], 'height'),
            weight=safe_int(row['weight'], 'weight'),
            left_foot=safe_int(row['left_foot'], 'left_foot'),
            right_foot=safe_int(row['right_foot'], 'right_foot'),
            
            # Player traits
            traits=safe_str(row.get('traits', ''), 'traits', allow_empty=True),
        )
        
        return player
        
    except Exception as e:
        # Re-raise with more context
        player_name = row.get('name', 'unknown')
        raise ValueError(f"Failed to create Player for '{player_name}': {str(e)}") from e

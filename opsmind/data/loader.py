"""
Data loading functions for OpsMind
"""
import pandas as pd
from pathlib import Path
from typing import Dict, Any

from opsmind.config import (
    INCIDENT_DATA_PATH,
    JIRA_ISSUES_PATH,
    JIRA_COMMENTS_PATH,
    JIRA_CHANGELOG_PATH,
    JIRA_ISSUELINKS_PATH,
    logger
)
from opsmind.utils import validate_csv_file


def load_incident_data() -> pd.DataFrame:
    """Load incident data from CSV file"""
    try:
        if not INCIDENT_DATA_PATH.exists():
            logger.warning(f"Incident data file not found: {INCIDENT_DATA_PATH}")
            return pd.DataFrame()
        
        df = pd.read_csv(INCIDENT_DATA_PATH, keep_default_na=False, na_values=[''])
        df = df.fillna('')
        logger.info(f"Loaded {len(df)} incident records from {INCIDENT_DATA_PATH}")
        return df
    except Exception as e:
        logger.error(f"Error loading incident data: {e}")
        return pd.DataFrame()


def load_jira_data() -> Dict[str, pd.DataFrame]:
    """Load all Jira data from CSV files"""
    jira_data = {}
    
    # Define file mappings
    file_mappings = {
        'issues': JIRA_ISSUES_PATH,
        'comments': JIRA_COMMENTS_PATH,
        'changelog': JIRA_CHANGELOG_PATH,
        'issuelinks': JIRA_ISSUELINKS_PATH
    }
    
    for data_type, file_path in file_mappings.items():
        try:
            if not file_path.exists():
                logger.warning(f"Jira {data_type} file not found: {file_path}")
                jira_data[data_type] = pd.DataFrame()
                continue
            
            df = pd.read_csv(file_path, keep_default_na=False, na_values=[''])
            df = df.fillna('')
            jira_data[data_type] = df
            logger.info(f"Loaded {len(df)} Jira {data_type} records from {file_path}")
            
        except Exception as e:
            logger.warning(f"Could not load Jira {data_type} from {file_path}: {e}")
            jira_data[data_type] = pd.DataFrame()
    
    return jira_data


def validate_data_files() -> bool:
    """Validate that all required data files exist and are readable"""
    file_mappings = {
        'incident data': INCIDENT_DATA_PATH,
        'Jira issues': JIRA_ISSUES_PATH,
        'Jira comments': JIRA_COMMENTS_PATH,
        'Jira changelog': JIRA_CHANGELOG_PATH,
        'Jira issue links': JIRA_ISSUELINKS_PATH
    }
    
    all_valid = True
    for file_type, file_path in file_mappings.items():
        if not validate_csv_file(file_path, file_type):
            all_valid = False
    
    if all_valid:
        logger.info("All required data files are valid")
    else:
        logger.warning("Some data files are missing or invalid")
    
    return all_valid 
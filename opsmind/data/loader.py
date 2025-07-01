"""
Data loading functions for OpsMind
"""
import pandas as pd
from ..config import (
    INCIDENT_DATA_PATH, 
    JIRA_ISSUES_PATH, 
    JIRA_COMMENTS_PATH, 
    JIRA_CHANGELOG_PATH, 
    JIRA_ISSUELINKS_PATH,
    logger
)

def load_incident_data():
    """Load incident data from CSV"""
    try:
        df = pd.read_csv(INCIDENT_DATA_PATH, keep_default_na=False, na_values=[''])
        # Replace any remaining NaN values with empty strings
        df = df.fillna('')
        logger.info(f"Loaded {len(df)} incident records")
        return df
    except Exception as e:
        logger.error(f"Error loading incident data: {e}")
        return pd.DataFrame()

def load_jira_data():
    """Load all Jira data from CSV files"""
    jira_data = {}
    try:
        # Load Jira issues
        issues_df = pd.read_csv(JIRA_ISSUES_PATH, keep_default_na=False, na_values=[''])
        issues_df = issues_df.fillna('')
        jira_data['issues'] = issues_df
        logger.info(f"Loaded {len(issues_df)} Jira issues")
        
        # Load Jira comments
        try:
            comments_df = pd.read_csv(JIRA_COMMENTS_PATH, keep_default_na=False, na_values=[''])
            comments_df = comments_df.fillna('')
            jira_data['comments'] = comments_df
            logger.info(f"Loaded {len(comments_df)} Jira comments")
        except Exception as e:
            logger.warning(f"Could not load Jira comments: {e}")
            jira_data['comments'] = pd.DataFrame()
        
        # Load Jira changelog
        try:
            changelog_df = pd.read_csv(JIRA_CHANGELOG_PATH, keep_default_na=False, na_values=[''])
            changelog_df = changelog_df.fillna('')
            jira_data['changelog'] = changelog_df
            logger.info(f"Loaded {len(changelog_df)} Jira changelog entries")
        except Exception as e:
            logger.warning(f"Could not load Jira changelog: {e}")
            jira_data['changelog'] = pd.DataFrame()
            
        # Load Jira issue links
        try:
            issuelinks_df = pd.read_csv(JIRA_ISSUELINKS_PATH, keep_default_na=False, na_values=[''])
            issuelinks_df = issuelinks_df.fillna('')
            jira_data['issuelinks'] = issuelinks_df
            logger.info(f"Loaded {len(issuelinks_df)} Jira issue links")
        except Exception as e:
            logger.warning(f"Could not load Jira issue links: {e}")
            jira_data['issuelinks'] = pd.DataFrame()
            
        return jira_data
    except Exception as e:
        logger.error(f"Error loading Jira data: {e}")
        return {'issues': pd.DataFrame(), 'comments': pd.DataFrame(), 
                'changelog': pd.DataFrame(), 'issuelinks': pd.DataFrame()} 
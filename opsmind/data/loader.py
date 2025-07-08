"""
Data loading functions for OpsMind
"""
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import re

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


def search_jira_issues(
    search_term: str = "",
    status: str = "",
    priority: str = "",
    assignee: str = "",
    project: str = "",
    issue_type: str = "",
    created_after: str = "",
    created_before: str = "",
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Search JIRA issues with various filters
    
    Args:
        search_term: Search in summary and description
        status: Filter by status name
        priority: Filter by priority name
        assignee: Filter by assignee
        project: Filter by project key or name
        issue_type: Filter by issue type
        created_after: Filter by creation date (YYYY-MM-DD)
        created_before: Filter by creation date (YYYY-MM-DD)
        limit: Maximum number of results to return
    
    Returns:
        List of matching issues
    """
    try:
        jira_data = load_jira_data()
        issues_df = jira_data.get('issues', pd.DataFrame())
        
        if issues_df.empty:
            logger.warning("No JIRA issues data available")
            return []
        
        # Apply filters
        filtered_df = issues_df.copy()
        
        # Search term filter - search in summary and description
        if search_term:
            search_mask = (
                filtered_df['summary'].str.contains(search_term, case=False, na=False) |
                filtered_df['description'].str.contains(search_term, case=False, na=False)
            )
            filtered_df = filtered_df[search_mask]
        
        # Status filter
        if status:
            filtered_df = filtered_df[filtered_df['status.name'].str.contains(status, case=False, na=False)]
        
        # Priority filter
        if priority:
            filtered_df = filtered_df[filtered_df['priority.name'].str.contains(priority, case=False, na=False)]
        
        # Assignee filter
        if assignee:
            filtered_df = filtered_df[filtered_df['assignee'].str.contains(assignee, case=False, na=False)]
        
        # Project filter
        if project:
            project_mask = (
                filtered_df['project.key'].str.contains(project, case=False, na=False) |
                filtered_df['project.name'].str.contains(project, case=False, na=False)
            )
            filtered_df = filtered_df[project_mask]
        
        # Issue type filter
        if issue_type:
            filtered_df = filtered_df[filtered_df['issuetype.name'].str.contains(issue_type, case=False, na=False)]
        
        # Date filters
        if created_after or created_before:
            try:
                # Convert created column to datetime
                filtered_df['created_dt'] = pd.to_datetime(filtered_df['created'], errors='coerce')
                
                if created_after:
                    after_date = pd.to_datetime(created_after)
                    filtered_df = filtered_df[filtered_df['created_dt'] >= after_date]
                
                if created_before:
                    before_date = pd.to_datetime(created_before)
                    filtered_df = filtered_df[filtered_df['created_dt'] <= before_date]
                
                # Remove the temporary datetime column
                filtered_df = filtered_df.drop('created_dt', axis=1)
            except Exception as e:
                logger.warning(f"Error applying date filters: {e}")
        
        # Limit results
        if limit > 0:
            filtered_df = filtered_df.head(limit)
        
        results = filtered_df.to_dict('records')
        logger.info(f"Found {len(results)} JIRA issues matching search criteria")
        return results
        
    except Exception as e:
        logger.error(f"Error searching JIRA issues: {e}")
        return []


def search_jira_comments(
    search_term: str = "",
    issue_key: str = "",
    author: str = "",
    created_after: str = "",
    created_before: str = "",
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Search JIRA comments with various filters
    
    Args:
        search_term: Search in comment body
        issue_key: Filter by specific issue key
        author: Filter by comment author
        created_after: Filter by creation date (YYYY-MM-DD)
        created_before: Filter by creation date (YYYY-MM-DD)
        limit: Maximum number of results to return
    
    Returns:
        List of matching comments
    """
    try:
        jira_data = load_jira_data()
        comments_df = jira_data.get('comments', pd.DataFrame())
        
        if comments_df.empty:
            logger.warning("No JIRA comments data available")
            return []
        
        # Apply filters
        filtered_df = comments_df.copy()
        
        # Search term filter
        if search_term:
            filtered_df = filtered_df[filtered_df['body'].str.contains(search_term, case=False, na=False)]
        
        # Issue key filter
        if issue_key:
            filtered_df = filtered_df[filtered_df['key'].str.contains(issue_key, case=False, na=False)]
        
        # Author filter
        if author:
            filtered_df = filtered_df[filtered_df['author'].str.contains(author, case=False, na=False)]
        
        # Date filters
        if created_after or created_before:
            try:
                # Convert created column to datetime
                filtered_df['created_dt'] = pd.to_datetime(filtered_df['created'], errors='coerce')
                
                if created_after:
                    after_date = pd.to_datetime(created_after)
                    filtered_df = filtered_df[filtered_df['created_dt'] >= after_date]
                
                if created_before:
                    before_date = pd.to_datetime(created_before)
                    filtered_df = filtered_df[filtered_df['created_dt'] <= before_date]
                
                # Remove the temporary datetime column
                filtered_df = filtered_df.drop('created_dt', axis=1)
            except Exception as e:
                logger.warning(f"Error applying date filters: {e}")
        
        # Limit results
        if limit > 0:
            filtered_df = filtered_df.head(limit)
        
        results = filtered_df.to_dict('records')
        logger.info(f"Found {len(results)} JIRA comments matching search criteria")
        return results
        
    except Exception as e:
        logger.error(f"Error searching JIRA comments: {e}")
        return []


def search_jira_changelog(
    issue_key: str = "",
    field: str = "",
    author: str = "",
    from_value: str = "",
    to_value: str = "",
    created_after: str = "",
    created_before: str = "",
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Search JIRA changelog entries with various filters
    
    Args:
        issue_key: Filter by specific issue key
        field: Filter by field name that changed
        author: Filter by change author
        from_value: Filter by from value
        to_value: Filter by to value
        created_after: Filter by creation date (YYYY-MM-DD)
        created_before: Filter by creation date (YYYY-MM-DD)
        limit: Maximum number of results to return
    
    Returns:
        List of matching changelog entries
    """
    try:
        jira_data = load_jira_data()
        changelog_df = jira_data.get('changelog', pd.DataFrame())
        
        if changelog_df.empty:
            logger.warning("No JIRA changelog data available")
            return []
        
        # Apply filters
        filtered_df = changelog_df.copy()
        
        # Issue key filter
        if issue_key:
            filtered_df = filtered_df[filtered_df['key'].str.contains(issue_key, case=False, na=False)]
        
        # Field filter
        if field:
            filtered_df = filtered_df[filtered_df['field'].str.contains(field, case=False, na=False)]
        
        # Author filter
        if author:
            filtered_df = filtered_df[filtered_df['author'].str.contains(author, case=False, na=False)]
        
        # From value filter
        if from_value:
            filtered_df = filtered_df[filtered_df['from'].str.contains(from_value, case=False, na=False)]
        
        # To value filter
        if to_value:
            filtered_df = filtered_df[filtered_df['to'].str.contains(to_value, case=False, na=False)]
        
        # Date filters
        if created_after or created_before:
            try:
                # Convert created column to datetime
                filtered_df['created_dt'] = pd.to_datetime(filtered_df['created'], errors='coerce')
                
                if created_after:
                    after_date = pd.to_datetime(created_after)
                    filtered_df = filtered_df[filtered_df['created_dt'] >= after_date]
                
                if created_before:
                    before_date = pd.to_datetime(created_before)
                    filtered_df = filtered_df[filtered_df['created_dt'] <= before_date]
                
                # Remove the temporary datetime column
                filtered_df = filtered_df.drop('created_dt', axis=1)
            except Exception as e:
                logger.warning(f"Error applying date filters: {e}")
        
        # Limit results
        if limit > 0:
            filtered_df = filtered_df.head(limit)
        
        results = filtered_df.to_dict('records')
        logger.info(f"Found {len(results)} JIRA changelog entries matching search criteria")
        return results
        
    except Exception as e:
        logger.error(f"Error searching JIRA changelog: {e}")
        return []


def get_jira_issue_details(issue_key: str) -> Dict[str, Any]:
    """
    Get complete details for a specific JIRA issue including comments and changelog
    
    Args:
        issue_key: The JIRA issue key to get details for
    
    Returns:
        Dictionary with issue details, comments, and changelog
    """
    try:
        jira_data = load_jira_data()
        
        # Get issue details
        issues_df = jira_data.get('issues', pd.DataFrame())
        issue_details = {}
        
        if not issues_df.empty:
            issue_row = issues_df[issues_df['key'] == issue_key]
            if not issue_row.empty:
                issue_details = issue_row.iloc[0].to_dict()
        
        # Get comments
        comments_df = jira_data.get('comments', pd.DataFrame())
        comments = []
        if not comments_df.empty:
            issue_comments = comments_df[comments_df['key'] == issue_key]
            comments = issue_comments.to_dict(orient='records')
        
        # Get changelog
        changelog_df = jira_data.get('changelog', pd.DataFrame())
        changelog = []
        if not changelog_df.empty:
            issue_changelog = changelog_df[changelog_df['key'] == issue_key]
            changelog = issue_changelog.to_dict('records')
        
        # Get issue links
        issuelinks_df = jira_data.get('issuelinks', pd.DataFrame())
        links = []
        if not issuelinks_df.empty:
            issue_links = issuelinks_df[
                (issuelinks_df['outwardIssue.key'] == issue_key) |
                (issuelinks_df['inwardIssue.key'] == issue_key)
            ]
            links = issue_links.to_dict('records')
        
        result = {
            'issue': issue_details,
            'comments': comments,
            'changelog': changelog,
            'links': links,
            'total_comments': len(comments),
            'total_changelog': len(changelog),
            'total_links': len(links)
        }
        
        logger.info(f"Retrieved details for JIRA issue {issue_key}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting JIRA issue details for {issue_key}: {e}")
        return {}


def validate_data_files() -> bool:
    """Validate that required data files exist and are readable"""
    files_to_check = [
        INCIDENT_DATA_PATH,
        JIRA_ISSUES_PATH,
        JIRA_COMMENTS_PATH,
        JIRA_CHANGELOG_PATH,
        JIRA_ISSUELINKS_PATH
    ]
    
    all_valid = True
    for file_path in files_to_check:
        if not validate_csv_file(file_path):
            all_valid = False
    
    return all_valid 
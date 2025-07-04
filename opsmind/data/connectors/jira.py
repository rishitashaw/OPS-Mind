"""
JIRA Real-time Connector for OpsMind RAG system
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, AsyncGenerator, cast
from urllib.parse import urljoin
import base64
import logging

from .base import BaseConnector, ConnectorConfig, DataRecord
from opsmind.config import get_jira_config, logger


def create_jira_connector(name: str = "jira_connector", **override_params) -> Optional['JiraConnector']:
    """
    Create a JIRA connector using environment configuration
    
    Args:
        name: Name for the connector
        **override_params: Override any configuration parameters
        
    Returns:
        JiraConnector instance or None if configuration is invalid
    """
    try:
        jira_config = get_jira_config()
        
        # Check if Jira is enabled and properly configured
        if not jira_config["enabled"]:
            logger.info("Jira connector is disabled in configuration")
            return None
        
        if not all([jira_config["base_url"], jira_config["username"], jira_config["api_token"]]):
            logger.warning("Jira connector configuration is incomplete")
            return None
        
        # Merge override parameters
        connection_params = {
            "base_url": jira_config["base_url"],
            "username": jira_config["username"],
            "api_token": jira_config["api_token"],
            "project_keys": jira_config["project_keys"],
            **override_params
        }
        
        # Create connector configuration
        config = ConnectorConfig(
            name=name,
            connector_type="jira",
            enabled=jira_config["enabled"],
            poll_interval=jira_config["poll_interval"],
            max_retries=jira_config["max_retries"],
            retry_delay=jira_config["retry_delay"],
            batch_size=jira_config["batch_size"],
            connection_params=connection_params
        )
        
        return JiraConnector(config)
        
    except Exception as e:
        logger.error(f"Error creating Jira connector: {e}")
        return None


class JiraConnector(BaseConnector):
    """Real-time JIRA connector for fetching issues, comments, and updates"""
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_sync_time: Optional[datetime] = None
        self.auth_header: Optional[str] = None
        
        # JIRA specific configuration - validate and assign
        base_url = config.connection_params.get('base_url')
        username = config.connection_params.get('username') 
        api_token = config.connection_params.get('api_token')
        
        if not all([base_url, username, api_token]):
            raise ValueError("JIRA connector requires base_url, username, and api_token")
        
        # Ensure types are correct after validation
        if not isinstance(base_url, str):
            raise ValueError("base_url must be a string")
        if not isinstance(username, str):
            raise ValueError("username must be a string")
        if not isinstance(api_token, str):
            raise ValueError("api_token must be a string")
        
        # Now assign with proper types
        self.base_url: str = base_url.rstrip('/')  # Remove trailing slash
        self.username: str = username
        self.api_token: str = api_token
        self.project_keys = config.connection_params.get('project_keys', [])
        self.jql_filter = config.connection_params.get('jql_filter', '')
    
    async def connect(self) -> bool:
        """Establish connection to JIRA"""
        try:
            # Create auth header
            auth_string = f"{self.username}:{self.api_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            self.auth_header = f"Basic {auth_b64}"
            
            # Create HTTP session
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'Authorization': self.auth_header,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            )
            
            # Test connection
            url = urljoin(self.base_url, '/rest/api/2/myself')
            async with self.session.get(url) as response:
                if response.status == 200:
                    user_info = await response.json()
                    logger.info(f"Connected to JIRA as {user_info.get('displayName', 'Unknown')}")
                    return True
                else:
                    logger.error(f"JIRA connection failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error connecting to JIRA: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close connection to JIRA"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def fetch_data(self) -> AsyncGenerator[List[DataRecord], None]:
        """Fetch data from JIRA - yields batches of records"""
        if not self.session:
            logger.error("JIRA session not established")
            return
        
        # Set last sync time if not set (start from 1 hour ago)
        if not self.last_sync_time:
            self.last_sync_time = datetime.now() - timedelta(hours=1)
        
        try:
            # Fetch recent issues
            issues = await self._fetch_recent_issues()
            if issues:
                yield issues
            
            # Fetch recent comments
            comments = await self._fetch_recent_comments()
            if comments:
                yield comments
            
            # Fetch recent worklogs
            worklogs = await self._fetch_recent_worklogs()
            if worklogs:
                yield worklogs
            
            # Update last sync time
            self.last_sync_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Error fetching JIRA data: {e}")
            raise
    
    async def _fetch_recent_issues(self) -> List[DataRecord]:
        """Fetch recently updated issues"""
        records = []
        
        if not self.session:
            return records
        
        try:
            # Build JQL query for recent updates
            jql_parts = []
            
            # Add project filter if specified
            if self.project_keys:
                project_filter = " OR ".join([f"project = {key}" for key in self.project_keys])
                jql_parts.append(f"({project_filter})")
            
            # Add time filter
            time_filter = f"updated >= -{self.config.poll_interval}m"
            jql_parts.append(time_filter)
            
            # Add custom JQL filter if specified
            if self.jql_filter:
                jql_parts.append(f"({self.jql_filter})")
            
            jql = " AND ".join(jql_parts)
            
            # Make API request
            url = urljoin(self.base_url, '/rest/api/2/search')
            params = {
                'jql': jql,
                'maxResults': self.config.batch_size,
                'expand': 'changelog',
                'fields': 'summary,description,status,priority,assignee,reporter,created,updated,components,labels,fixVersions,customfield_*'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for issue in data.get('issues', []):
                        record = self._convert_issue_to_record(issue)
                        records.append(record)
                        
                        # Also create records for changelog entries
                        changelog_records = self._extract_changelog_records(issue)
                        records.extend(changelog_records)
                        
                else:
                    logger.warning(f"Failed to fetch issues: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error fetching recent issues: {e}")
        
        return records
    
    async def _fetch_recent_comments(self) -> List[DataRecord]:
        """Fetch recent comments across projects"""
        records = []
        
        if not self.session:
            return records
        
        try:
            # Get recently updated issues first (they might have new comments)
            jql_parts = []
            
            if self.project_keys:
                project_filter = " OR ".join([f"project = {key}" for key in self.project_keys])
                jql_parts.append(f"({project_filter})")
            
            # Look for issues updated in the last poll interval
            time_filter = f"updated >= -{self.config.poll_interval}m"
            jql_parts.append(time_filter)
            
            jql = " AND ".join(jql_parts)
            
            url = urljoin(self.base_url, '/rest/api/2/search')
            params = {
                'jql': jql,
                'maxResults': self.config.batch_size,
                'fields': 'key'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # For each issue, fetch recent comments
                    for issue in data.get('issues', []):
                        issue_key = issue['key']
                        comment_records = await self._fetch_issue_comments(issue_key)
                        records.extend(comment_records)
                        
        except Exception as e:
            logger.error(f"Error fetching recent comments: {e}")
        
        return records
    
    async def _fetch_issue_comments(self, issue_key: str) -> List[DataRecord]:
        """Fetch comments for a specific issue"""
        records = []
        
        if not self.session:
            return records
        
        try:
            url = urljoin(self.base_url, f'/rest/api/2/issue/{issue_key}/comment')
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for comment in data.get('comments', []):
                        # Only include recent comments
                        comment_created = datetime.fromisoformat(
                            comment['created'].replace('Z', '+00:00')
                        )
                        
                        if self.last_sync_time and comment_created >= self.last_sync_time:
                            record = DataRecord(
                                id=f"jira_comment_{comment['id']}",
                                source="jira",
                                type="comment",
                                timestamp=comment_created,
                                data={
                                    'issue_key': issue_key,
                                    'comment_id': comment['id'],
                                    'body': comment['body'],
                                    'author': comment['author']['displayName'],
                                    'author_email': comment['author'].get('emailAddress', ''),
                                    'created': comment['created'],
                                    'updated': comment.get('updated', comment['created']),
                                    'visibility': comment.get('visibility', {})
                                },
                                metadata={
                                    'jira_url': f"{self.base_url}/browse/{issue_key}",
                                    'connector': self.config.name
                                }
                            )
                            records.append(record)
                            
        except Exception as e:
            logger.error(f"Error fetching comments for {issue_key}: {e}")
        
        return records
    
    async def _fetch_recent_worklogs(self) -> List[DataRecord]:
        """Fetch recent worklogs"""
        records = []
        
        if not self.session:
            return records
        
        try:
            # Similar approach to comments - get recently updated issues
            jql_parts = []
            
            if self.project_keys:
                project_filter = " OR ".join([f"project = {key}" for key in self.project_keys])
                jql_parts.append(f"({project_filter})")
            
            time_filter = f"worklogDate >= -{self.config.poll_interval}m"
            jql_parts.append(time_filter)
            
            jql = " AND ".join(jql_parts)
            
            url = urljoin(self.base_url, '/rest/api/2/search')
            params = {
                'jql': jql,
                'maxResults': self.config.batch_size,
                'fields': 'key,worklog'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for issue in data.get('issues', []):
                        issue_key = issue['key']
                        worklog_records = await self._fetch_issue_worklogs(issue_key)
                        records.extend(worklog_records)
                        
        except Exception as e:
            logger.error(f"Error fetching recent worklogs: {e}")
        
        return records
    
    async def _fetch_issue_worklogs(self, issue_key: str) -> List[DataRecord]:
        """Fetch worklogs for a specific issue"""
        records = []
        
        if not self.session:
            return records
        
        try:
            url = urljoin(self.base_url, f'/rest/api/2/issue/{issue_key}/worklog')
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for worklog in data.get('worklogs', []):
                        # Only include recent worklogs
                        worklog_created = datetime.fromisoformat(
                            worklog['created'].replace('Z', '+00:00')
                        )
                        
                        if self.last_sync_time and worklog_created >= self.last_sync_time:
                            record = DataRecord(
                                id=f"jira_worklog_{worklog['id']}",
                                source="jira",
                                type="worklog",
                                timestamp=worklog_created,
                                data={
                                    'issue_key': issue_key,
                                    'worklog_id': worklog['id'],
                                    'time_spent': worklog['timeSpent'],
                                    'time_spent_seconds': worklog['timeSpentSeconds'],
                                    'comment': worklog.get('comment', ''),
                                    'author': worklog['author']['displayName'],
                                    'author_email': worklog['author'].get('emailAddress', ''),
                                    'created': worklog['created'],
                                    'updated': worklog.get('updated', worklog['created']),
                                    'started': worklog['started']
                                },
                                metadata={
                                    'jira_url': f"{self.base_url}/browse/{issue_key}",
                                    'connector': self.config.name
                                }
                            )
                            records.append(record)
                            
        except Exception as e:
            logger.error(f"Error fetching worklogs for {issue_key}: {e}")
        
        return records
    
    def _convert_issue_to_record(self, issue: Dict[str, Any]) -> DataRecord:
        """Convert JIRA issue to DataRecord"""
        fields = issue['fields']
        
        return DataRecord(
            id=f"jira_issue_{issue['key']}",
            source="jira",
            type="issue",
            timestamp=datetime.fromisoformat(fields['updated'].replace('Z', '+00:00')),
            data={
                'key': issue['key'],
                'summary': fields.get('summary', ''),
                'description': fields.get('description', ''),
                'status': fields.get('status', {}).get('name', ''),
                'status_category': fields.get('status', {}).get('statusCategory', {}).get('name', ''),
                'priority': fields.get('priority', {}).get('name', ''),
                'assignee': fields.get('assignee', {}).get('displayName', '') if fields.get('assignee') else '',
                'assignee_email': fields.get('assignee', {}).get('emailAddress', '') if fields.get('assignee') else '',
                'reporter': fields.get('reporter', {}).get('displayName', '') if fields.get('reporter') else '',
                'reporter_email': fields.get('reporter', {}).get('emailAddress', '') if fields.get('reporter') else '',
                'created': fields.get('created', ''),
                'updated': fields.get('updated', ''),
                'components': [comp['name'] for comp in fields.get('components', [])],
                'labels': fields.get('labels', []),
                'fix_versions': [ver['name'] for ver in fields.get('fixVersions', [])],
                'custom_fields': {k: v for k, v in fields.items() if k.startswith('customfield_')}
            },
            metadata={
                'jira_url': f"{self.base_url}/browse/{issue['key']}",
                'connector': self.config.name
            }
        )
    
    def _extract_changelog_records(self, issue: Dict[str, Any]) -> List[DataRecord]:
        """Extract changelog entries as separate records"""
        records = []
        
        changelog = issue.get('changelog', {})
        for history in changelog.get('histories', []):
            history_created = datetime.fromisoformat(
                history['created'].replace('Z', '+00:00')
            )
            
            # Only include recent changelog entries
            if self.last_sync_time and history_created >= self.last_sync_time:
                for item in history.get('items', []):
                    record = DataRecord(
                        id=f"jira_changelog_{issue['key']}_{history['id']}_{item['field']}",
                        source="jira",
                        type="changelog",
                        timestamp=history_created,
                        data={
                            'issue_key': issue['key'],
                            'history_id': history['id'],
                            'field': item['field'],
                            'field_type': item['fieldtype'],
                            'from_string': item.get('fromString', ''),
                            'to_string': item.get('toString', ''),
                            'from_value': item.get('from', ''),
                            'to_value': item.get('to', ''),
                            'author': history['author']['displayName'],
                            'author_email': history['author'].get('emailAddress', ''),
                            'created': history['created']
                        },
                        metadata={
                            'jira_url': f"{self.base_url}/browse/{issue['key']}",
                            'connector': self.config.name
                        }
                    )
                    records.append(record)
        
        return records 
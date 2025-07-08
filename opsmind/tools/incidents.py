"""
Incident processing tools for OpsMind
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import re
import json
import pandas as pd

from google.adk.tools.tool_context import ToolContext
from opsmind.config import logger
from opsmind.utils import safe_json_loads
from opsmind.data.loader import (
    load_incident_data,
    load_jira_data,
    search_jira_issues,
    search_jira_comments,
    search_jira_changelog,
    get_jira_issue_details
)

def process_incident_stream(
    tool_context: ToolContext,
    incident_data: str
) -> Dict[str, str]:
    """Process incident data and add to context for RAG"""
    try:
        incident_info = safe_json_loads(incident_data)
        existing_incidents = tool_context.state.get("incident_stream", [])
        tool_context.state["incident_stream"] = existing_incidents + [incident_info]
        logger.info(f"Added incident {incident_info.get('number', 'unknown')} to stream")
        return {"status": "success", "message": f"Processed incident {incident_info.get('number', 'unknown')}"}
    except Exception as e:
        logger.error(f"Error processing incident: {e}")
        return {"status": "error", "message": str(e)}

def create_incident_summary(
    tool_context: ToolContext,
    incident_id: str,
    summary_text: str
) -> Dict[str, str]:
    """Create incident summary and store for postmortem generation"""
    summaries = tool_context.state.get("incident_summaries", {})
    summaries[incident_id] = {
        "id": incident_id,
        "summary": summary_text,
        "timestamp": datetime.now().isoformat(),
        "status": "summarized"
    }
    tool_context.state["incident_summaries"] = summaries
    logger.info(f"Created summary for incident {incident_id}")
    return {"status": "success", "incident_id": incident_id}

def search_incidents(
    tool_context: ToolContext,
    search_term: str = "",
    incident_state: str = "",
    priority: str = "",
    category: str = "",
    assignment_group: str = "",
    opened_after: str = "",
    opened_before: str = "",
    limit: int = 50
) -> Dict[str, Any]:
    """
    Search incidents with various filters
    
    Args:
        search_term: Search in symptom, category, subcategory
        incident_state: Filter by incident state
        priority: Filter by priority
        category: Filter by category
        assignment_group: Filter by assignment group
        opened_after: Filter by opened date (YYYY-MM-DD)
        opened_before: Filter by opened date (YYYY-MM-DD)
        limit: Maximum number of results to return
    
    Returns:
        Dictionary with search results and metadata
    """
    try:
        incidents_df = load_incident_data()
        
        if incidents_df.empty:
            logger.warning("No incident data available")
            return {"incidents": [], "total_count": 0, "search_info": "No incident data available"}
        
        # Apply filters
        filtered_df = incidents_df.copy()
        
        # Search term filter - search in symptom, category, subcategory
        if search_term:
            search_mask = (
                filtered_df['u_symptom'].str.contains(search_term, case=False, na=False) |
                filtered_df['category'].str.contains(search_term, case=False, na=False) |
                filtered_df['subcategory'].str.contains(search_term, case=False, na=False)
            )
            filtered_df = filtered_df[search_mask]
        
        # State filter
        if incident_state:
            filtered_df = filtered_df[filtered_df['incident_state'].str.contains(incident_state, case=False, na=False)]
        
        # Priority filter
        if priority:
            filtered_df = filtered_df[filtered_df['priority'].str.contains(priority, case=False, na=False)]
        
        # Category filter
        if category:
            filtered_df = filtered_df[filtered_df['category'].astype(str).str.contains(category, case=False, na=False)]
        
        # Assignment group filter
        if assignment_group:
            filtered_df = filtered_df[filtered_df['assignment_group'].astype(str).str.contains(assignment_group, case=False, na=False)]
        
        # Date filters
        if opened_after or opened_before:
            try:
                # Convert opened_at column to datetime
                filtered_df['opened_dt'] = pd.to_datetime(filtered_df['opened_at'], errors='coerce')
                
                if opened_after:
                    after_date = pd.to_datetime(opened_after)
                    filtered_df = filtered_df[filtered_df['opened_dt'] >= after_date]
                
                if opened_before:
                    before_date = pd.to_datetime(opened_before)
                    filtered_df = filtered_df[filtered_df['opened_dt'] <= before_date]
                
                # Remove the temporary datetime column
                filtered_df = filtered_df.drop('opened_dt', axis=1)
            except Exception as e:
                logger.warning(f"Error applying date filters: {e}")
        
        # Limit results
        if limit > 0:
            filtered_df = filtered_df.head(limit)
        
        results = filtered_df.to_dict('records')
        
        # Store in context for further processing
        tool_context.state["last_incident_search"] = {
            "results": results,
            "search_params": {
                "search_term": search_term,
                "incident_state": incident_state,
                "priority": priority,
                "category": category,
                "assignment_group": assignment_group,
                "opened_after": opened_after,
                "opened_before": opened_before,
                "limit": limit
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Found {len(results)} incidents matching search criteria")
        return {
            "incidents": results,
            "total_count": len(results),
            "search_info": f"Found {len(results)} incidents matching criteria"
        }
        
    except Exception as e:
        logger.error(f"Error searching incidents: {e}")
        return {"incidents": [], "total_count": 0, "search_info": f"Error: {str(e)}"}

def correlate_incident_with_jira(
    tool_context: ToolContext,
    incident_id: str,
    time_window_hours: int = 24,
    search_keywords: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Correlate an incident with JIRA issues, comments, and changelog entries
    
    Args:
        incident_id: The incident ID to correlate
        time_window_hours: Time window to search for related JIRA activity
        search_keywords: Additional keywords to search for in JIRA data
    
    Returns:
        Dictionary with correlation results
    """
    try:
        # Load incident data
        incidents_df = load_incident_data()
        incident_data = incidents_df[incidents_df['number'] == incident_id].to_dict(orient='records')
        
        if not incident_data:
            return {
                "incident_found": False,
                "message": f"Incident {incident_id} not found"
            }
        
        incident = incident_data[0]
        
        # Extract search terms from incident
        search_terms = []
        if search_keywords:
            search_terms.extend(search_keywords)
        
        # Add incident-specific search terms
        if incident.get('u_symptom'):
            search_terms.append(incident['u_symptom'])
        if incident.get('category'):
            search_terms.append(incident['category'])
        if incident.get('subcategory'):
            search_terms.append(incident['subcategory'])
        
        # Calculate time window
        try:
            opened_at = pd.to_datetime(incident.get('opened_at', ''))
            start_time = opened_at - timedelta(hours=time_window_hours)
            end_time = opened_at + timedelta(hours=time_window_hours)
            
            start_date = start_time.strftime('%Y-%m-%d')
            end_date = end_time.strftime('%Y-%m-%d')
        except:
            # If date parsing fails, use a broader search
            start_date = ""
            end_date = ""
        
        # Search for related JIRA issues
        related_issues = []
        related_comments = []
        related_changelog = []
        
        for term in search_terms:
            if term and term.strip():
                # Search in issues
                issues = search_jira_issues(
                    search_term=term,
                    created_after=start_date,
                    created_before=end_date,
                    limit=20
                )
                related_issues.extend(issues)
                
                # Search in comments
                comments = search_jira_comments(
                    search_term=term,
                    created_after=start_date,
                    created_before=end_date,
                    limit=20
                )
                related_comments.extend(comments)
                
                # Search in changelog
                changelog = search_jira_changelog(
                    created_after=start_date,
                    created_before=end_date,
                    limit=20
                )
                related_changelog.extend(changelog)
        
        # Remove duplicates
        related_issues = list({issue['key']: issue for issue in related_issues if issue.get('key')}.values())
        related_comments = list({f"{comment['key']}-{comment['comment.id']}": comment for comment in related_comments if comment.get('key')}.values())
        related_changelog = list({f"{change['key']}-{change['id']}": change for change in related_changelog if change.get('key')}.values())
        
        result = {
            "incident_found": True,
            "incident": incident,
            "correlation_results": {
                "related_issues": related_issues,
                "related_comments": related_comments,
                "related_changelog": related_changelog
            },
            "summary": {
                "incident_id": incident_id,
                "issues_count": len(related_issues),
                "comments_count": len(related_comments),
                "changelog_count": len(related_changelog),
                "time_window_hours": time_window_hours,
                "search_terms": search_terms
            }
        }
        
        # Store in context
        tool_context.state["last_incident_correlation"] = result
        
        logger.info(f"Correlated incident {incident_id} with {len(related_issues)} issues, {len(related_comments)} comments, {len(related_changelog)} changelog entries")
        return result
        
    except Exception as e:
        logger.error(f"Error correlating incident {incident_id} with JIRA: {e}")
        return {
            "incident_found": False,
            "message": f"Error correlating incident: {str(e)}"
        }

def search_jira_for_incidents(
    tool_context: ToolContext,
    incident_numbers: Optional[List[str]] = None,
    incident_keywords: Optional[List[str]] = None,
    search_in_comments: bool = True,
    search_in_changelog: bool = True,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Search JIRA data for references to specific incidents or incident-related keywords
    
    Args:
        incident_numbers: List of incident numbers to search for
        incident_keywords: List of incident-related keywords
        search_in_comments: Whether to search in comments
        search_in_changelog: Whether to search in changelog
        limit: Maximum number of results per search type
    
    Returns:
        Dictionary with search results from JIRA
    """
    try:
        search_terms = []
        
        if incident_numbers:
            search_terms.extend(incident_numbers)
        
        if incident_keywords:
            search_terms.extend(incident_keywords)
        
        if not search_terms:
            return {
                "message": "No search terms provided",
                "results": {}
            }
        
        results = {
            "issues": [],
            "comments": [],
            "changelog": []
        }
        
        # Search in issues
        for term in search_terms:
            if term and term.strip():
                issues = search_jira_issues(search_term=term, limit=limit)
                results["issues"].extend(issues)
        
        # Search in comments if requested
        if search_in_comments:
            for term in search_terms:
                if term and term.strip():
                    comments = search_jira_comments(search_term=term, limit=limit)
                    results["comments"].extend(comments)
        
        # Search in changelog if requested
        if search_in_changelog:
            for term in search_terms:
                if term and term.strip():
                    # Search in changelog descriptions and comments
                    changelog = search_jira_changelog(from_value=term, limit=limit)
                    results["changelog"].extend(changelog)
                    
                    # Also search in to_value
                    changelog2 = search_jira_changelog(to_value=term, limit=limit)
                    results["changelog"].extend(changelog2)
        
        # Remove duplicates
        results["issues"] = list({issue['key']: issue for issue in results["issues"] if issue.get('key')}.values())
        results["comments"] = list({f"{comment['key']}-{comment['comment.id']}": comment for comment in results["comments"] if comment.get('key')}.values())
        results["changelog"] = list({f"{change['key']}-{change['id']}": change for change in results["changelog"] if change.get('key')}.values())
        
        summary = {
            "search_terms": search_terms,
            "issues_found": len(results["issues"]),
            "comments_found": len(results["comments"]),
            "changelog_found": len(results["changelog"]),
            "total_found": len(results["issues"]) + len(results["comments"]) + len(results["changelog"])
        }
        
        # Store in context
        tool_context.state["last_jira_incident_search"] = {
            "results": results,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Found {summary['total_found']} JIRA items related to incidents")
        return {
            "results": results,
            "summary": summary,
            "message": f"Found {summary['total_found']} JIRA items related to incidents"
        }
        
    except Exception as e:
        logger.error(f"Error searching JIRA for incidents: {e}")
        return {
            "message": f"Error searching JIRA: {str(e)}",
            "results": {}
        }

def get_incident_jira_timeline(
    tool_context: ToolContext,
    incident_id: str,
    jira_issue_key: Optional[str] = None,
    time_window_hours: int = 48
) -> Dict[str, Any]:
    """
    Get a timeline of incident events and related JIRA activity
    
    Args:
        incident_id: The incident ID to create timeline for
        jira_issue_key: Optional specific JIRA issue key to include
        time_window_hours: Time window around incident to search for JIRA activity
    
    Returns:
        Dictionary with timeline events and metadata
    """
    try:
        # Load incident data
        incidents_df = load_incident_data()
        incident_data = incidents_df[incidents_df['number'] == incident_id].to_dict(orient='records')
        
        if not incident_data:
            return {
                "incident_found": False,
                "message": f"Incident {incident_id} not found"
            }
        
        incident = incident_data[0]
        incident_time = pd.to_datetime(incident.get('opened_at', ''), errors='coerce')
        
        if pd.isna(incident_time):
            return {
                "incident_found": True,
                "timeline": [],
                "message": "Incident found but no valid timestamp"
            }
        
        # Calculate time window
        start_time = incident_time - timedelta(hours=time_window_hours)
        end_time = incident_time + timedelta(hours=time_window_hours)
        
        timeline = []
        
        # Add incident events
        timeline.append({
            "timestamp": incident.get('opened_at', ''),
            "event_type": "incident_opened",
            "source": "incident",
            "description": f"Incident {incident_id} opened: {incident.get('u_symptom', 'No description')}",
            "priority": incident.get('priority', ''),
            "category": incident.get('category', ''),
            "assignment_group": incident.get('assignment_group', ''),
            "details": {
                "incident_number": incident.get('number', ''),
                "incident_state": incident.get('incident_state', ''),
                "subcategory": incident.get('subcategory', ''),
                "impact": incident.get('impact', ''),
                "urgency": incident.get('urgency', '')
            }
        })
        
        # Add close event if available
        if incident.get('closed_at'):
            timeline.append({
                "timestamp": incident.get('closed_at', ''),
                "event_type": "incident_closed", 
                "source": "incident",
                "description": f"Incident {incident_id} closed",
                "details": {
                    "incident_number": incident.get('number', ''),
                    "resolution": incident.get('resolution', '')
                }
            })
        
        # Load JIRA data
        jira_data = load_jira_data()
        
        # Add JIRA issue events
        issues_df = jira_data.get('issues', pd.DataFrame())
        if not issues_df.empty:
            issues_df['created_dt'] = pd.to_datetime(issues_df['created'], errors='coerce')
            issues_df['updated_dt'] = pd.to_datetime(issues_df['updated'], errors='coerce')
            
            # Filter by time window or specific issue
            if jira_issue_key:
                related_issues = issues_df[issues_df['key'] == jira_issue_key]
            else:
                related_issues = issues_df[
                    (issues_df['created_dt'] >= start_time) & 
                    (issues_df['created_dt'] <= end_time)
                ]
            
            for _, issue in related_issues.iterrows():
                timeline.append({
                    "timestamp": issue.get('created', ''),
                    "event_type": "jira_issue_created",
                    "source": "jira",
                    "description": f"JIRA issue {issue['key']} created: {issue.get('summary', '')}",
                    "priority": issue.get('priority.name', ''),
                    "status": issue.get('status.name', ''),
                    "details": {
                        "jira_key": issue.get('key', ''),
                        "project": issue.get('project.key', ''),
                        "issue_type": issue.get('issuetype.name', ''),
                        "assignee": issue.get('assignee', ''),
                        "description": issue.get('description', '')
                    }
                })
                
                # Add update event if different from created
                if issue.get('updated') != issue.get('created'):
                    timeline.append({
                        "timestamp": issue.get('updated', ''),
                        "event_type": "jira_issue_updated",
                        "source": "jira",
                        "description": f"JIRA issue {issue['key']} updated",
                        "details": {
                            "jira_key": issue.get('key', ''),
                            "current_status": issue.get('status.name', ''),
                            "current_assignee": issue.get('assignee', '')
                        }
                    })
        
        # Add JIRA comments
        comments_df = jira_data.get('comments', pd.DataFrame())
        if not comments_df.empty:
            comments_df['created_dt'] = pd.to_datetime(comments_df['created'], errors='coerce')
            
            # Filter by time window or specific issue
            if jira_issue_key:
                related_comments = comments_df[comments_df['key'] == jira_issue_key]
            else:
                related_comments = comments_df[
                    (comments_df['created_dt'] >= start_time) & 
                    (comments_df['created_dt'] <= end_time)
                ]
            
            for _, comment in related_comments.iterrows():
                timeline.append({
                    "timestamp": comment.get('created', ''),
                    "event_type": "jira_comment_added",
                    "source": "jira",
                    "description": f"Comment added to JIRA issue {comment['key']}",
                    "details": {
                        "jira_key": comment.get('key', ''),
                        "author": comment.get('author', ''),
                        "comment_body": comment.get('body', '')[:200] + "..." if len(str(comment.get('body', ''))) > 200 else comment.get('body', '')
                    }
                })
        
        # Add JIRA changelog events
        changelog_df = jira_data.get('changelog', pd.DataFrame())
        if not changelog_df.empty:
            changelog_df['created_dt'] = pd.to_datetime(changelog_df['created'], errors='coerce')
            
            # Filter by time window or specific issue
            if jira_issue_key:
                related_changelog = changelog_df[changelog_df['key'] == jira_issue_key]
            else:
                related_changelog = changelog_df[
                    (changelog_df['created_dt'] >= start_time) & 
                    (changelog_df['created_dt'] <= end_time)
                ]
            
            for _, change in related_changelog.iterrows():
                timeline.append({
                    "timestamp": change.get('created', ''),
                    "event_type": "jira_field_changed",
                    "source": "jira",
                    "description": f"JIRA issue {change['key']} field '{change.get('field', '')}' changed",
                    "details": {
                        "jira_key": change.get('key', ''),
                        "field": change.get('field', ''),
                        "from_value": change.get('from', ''),
                        "to_value": change.get('to', ''),
                        "author": change.get('author', '')
                    }
                })
        
        # Sort timeline by timestamp
        def parse_timestamp(entry):
            try:
                return pd.to_datetime(entry['timestamp'])
            except:
                return pd.to_datetime('1970-01-01')  # Default for invalid timestamps
        
        timeline.sort(key=parse_timestamp)
        
        # Store in context for further processing
        tool_context.state["last_incident_timeline"] = {
            "incident_id": incident_id,
            "timeline": timeline,
            "time_window_hours": time_window_hours,
            "jira_issue_key": jira_issue_key,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Created timeline for incident {incident_id} with {len(timeline)} events")
        return {
            "incident_found": True,
            "incident_id": incident_id,
            "timeline": timeline,
            "total_events": len(timeline),
            "time_window_hours": time_window_hours,
            "jira_issue_key": jira_issue_key,
            "message": f"Created timeline with {len(timeline)} events"
        }
        
    except Exception as e:
        logger.error(f"Error creating timeline for incident {incident_id}: {e}")
        return {
            "incident_found": False,
            "message": f"Error creating timeline: {str(e)}"
        } 
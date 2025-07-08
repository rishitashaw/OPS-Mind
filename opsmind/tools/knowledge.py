"""
Knowledge Repository Tools for OpsMind - SRE/DevOps Knowledge Base
"""
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from google.adk.tools.tool_context import ToolContext
from opsmind.config import logger
from opsmind.data.loader import (
    load_incident_data,
    load_jira_data,
    search_jira_issues,
    search_jira_comments,
    search_jira_changelog,
    get_jira_issue_details
)
from opsmind.context import get_incident_context
from opsmind.utils import safe_get
import pandas as pd


def search_knowledge_base(
    tool_context: ToolContext,
    query: str,
    limit: int = 20,
    include_incidents: bool = True,
    include_jira_issues: bool = True,
    include_jira_comments: bool = True,
    include_jira_changelog: bool = True
) -> Dict[str, Any]:
    """
    Comprehensive search across the entire knowledge base for SRE/DevOps questions
    
    Args:
        query: The question or search terms
        limit: Maximum number of results per data source
        include_incidents: Include incident data in search
        include_jira_issues: Include JIRA issues in search
        include_jira_comments: Include JIRA comments in search
        include_jira_changelog: Include JIRA changelog in search
    
    Returns:
        Dictionary with comprehensive search results from all data sources
    """
    try:
        logger.info(f"Searching knowledge base for: {query}")
        
        # Extract key terms from the query
        search_terms = _extract_search_terms(query)
        
        results = {
            "query": query,
            "search_terms": search_terms,
            "results": {},
            "total_results": 0,
            "search_timestamp": datetime.now().isoformat()
        }
        
        # Search incidents
        if include_incidents:
            incident_results = _search_incidents_comprehensive(search_terms, limit)
            results["results"]["incidents"] = incident_results
            results["total_results"] += len(incident_results)
        
        # Search JIRA issues
        if include_jira_issues:
            jira_issue_results = _search_jira_issues_comprehensive(search_terms, limit)
            results["results"]["jira_issues"] = jira_issue_results
            results["total_results"] += len(jira_issue_results)
        
        # Search JIRA comments
        if include_jira_comments:
            jira_comment_results = _search_jira_comments_comprehensive(search_terms, limit)
            results["results"]["jira_comments"] = jira_comment_results
            results["total_results"] += len(jira_comment_results)
        
        # Search JIRA changelog
        if include_jira_changelog:
            jira_changelog_results = _search_jira_changelog_comprehensive(search_terms, limit)
            results["results"]["jira_changelog"] = jira_changelog_results
            results["total_results"] += len(jira_changelog_results)
        
        # Store results in context for follow-up questions
        tool_context.state["last_knowledge_search"] = results
        
        # Generate summary
        results["summary"] = _generate_search_summary(results)
        
        logger.info(f"Knowledge base search completed: {results['total_results']} total results")
        return results
        
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        return {
            "query": query,
            "error": str(e),
            "total_results": 0,
            "search_timestamp": datetime.now().isoformat()
        }


def answer_devops_question(
    tool_context: ToolContext,
    question: str,
    search_limit: int = 15
) -> Dict[str, Any]:
    """
    Answer a DevOps/SRE question using the knowledge base
    
    Args:
        question: The DevOps/SRE question to answer
        search_limit: Limit for knowledge base search
    
    Returns:
        Dictionary with answer and supporting evidence
    """
    try:
        logger.info(f"Answering DevOps question: {question}")
        
        # Search the knowledge base
        search_results = search_knowledge_base(
            tool_context=tool_context,
            query=question,
            limit=search_limit
        )
        
        # Analyze results and generate answer
        answer_data = _analyze_results_for_answer(question, search_results)
        
        # Determine if we have sufficient information
        has_sufficient_info = (
            search_results["total_results"] > 0 and 
            answer_data["confidence"] > 0.3
        )
        
        if has_sufficient_info:
            return {
                "question": question,
                "answer_found": True,
                "answer": answer_data["answer"],
                "confidence": answer_data["confidence"],
                "supporting_evidence": answer_data["evidence"],
                "search_results": search_results,
                "fallback_needed": False,
                "source": "knowledge_base"
            }
        else:
            # Knowledge base doesn't have sufficient information
            return {
                "question": question,
                "answer_found": False,
                "message": "Insufficient information found in knowledge base. Web search recommended.",
                "partial_answer": answer_data["answer"] if answer_data["answer"] else None,
                "confidence": answer_data["confidence"],
                "supporting_evidence": answer_data["evidence"],
                "search_results": search_results,
                "fallback_needed": True,
                "source": "knowledge_base_insufficient"
            }
        
    except Exception as e:
        logger.error(f"Error answering DevOps question: {e}")
        return {
            "question": question,
            "answer_found": False,
            "error": str(e),
            "fallback_needed": True,
            "source": "error"
        }


def find_similar_issues(
    tool_context: ToolContext,
    issue_description: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Find similar issues from historical data
    
    Args:
        issue_description: Description of the current issue
        limit: Maximum number of similar issues to return
    
    Returns:
        Dictionary with similar issues and their resolutions
    """
    try:
        logger.info(f"Finding similar issues for: {issue_description}")
        
        # Search for similar incidents and issues
        search_results = search_knowledge_base(
            tool_context=tool_context,
            query=issue_description,
            limit=limit
        )
        
        # Extract similar issues with resolutions
        similar_issues = []
        
        # Process incidents
        for incident in search_results["results"].get("incidents", []):
            if incident.get("resolution") and incident.get("resolution") != "":
                similar_issues.append({
                    "type": "incident",
                    "id": incident.get("number"),
                    "title": incident.get("short_description", ""),
                    "description": incident.get("description", ""),
                    "resolution": incident.get("resolution", ""),
                    "category": incident.get("category", ""),
                    "priority": incident.get("priority", ""),
                    "state": incident.get("incident_state", "")
                })
        
        # Process JIRA issues
        for issue in search_results["results"].get("jira_issues", []):
            if issue.get("status.name") in ["Resolved", "Closed", "Done"]:
                similar_issues.append({
                    "type": "jira_issue",
                    "id": issue.get("key"),
                    "title": issue.get("summary", ""),
                    "description": issue.get("description", ""),
                    "resolution": issue.get("resolution.name", ""),
                    "status": issue.get("status.name", ""),
                    "priority": issue.get("priority.name", ""),
                    "project": issue.get("project.key", "")
                })
        
        # Sort by relevance (simplified scoring)
        similar_issues.sort(key=lambda x: len(x.get("resolution", "")), reverse=True)
        
        return {
            "query": issue_description,
            "similar_issues": similar_issues[:limit],
            "total_found": len(similar_issues),
            "search_results": search_results
        }
        
    except Exception as e:
        logger.error(f"Error finding similar issues: {e}")
        return {
            "query": issue_description,
            "similar_issues": [],
            "total_found": 0,
            "error": str(e)
        }


def get_historical_patterns(
    tool_context: ToolContext,
    pattern_type: str = "all",
    time_period_days: int = 365
) -> Dict[str, Any]:
    """
    Get historical patterns from the knowledge base
    
    Args:
        pattern_type: Type of patterns to analyze (all, incidents, jira, failures)
        time_period_days: Time period to analyze
    
    Returns:
        Dictionary with historical patterns and insights
    """
    try:
        logger.info(f"Analyzing historical patterns: {pattern_type}")
        
        patterns = {
            "pattern_type": pattern_type,
            "time_period_days": time_period_days,
            "analysis_timestamp": datetime.now().isoformat(),
            "patterns": {}
        }
        
        # Analyze incident patterns
        if pattern_type in ["all", "incidents"]:
            patterns["patterns"]["incidents"] = _analyze_incident_patterns(time_period_days)
        
        # Analyze JIRA patterns
        if pattern_type in ["all", "jira"]:
            patterns["patterns"]["jira"] = _analyze_jira_patterns(time_period_days)
        
        # Analyze failure patterns
        if pattern_type in ["all", "failures"]:
            patterns["patterns"]["failures"] = _analyze_failure_patterns(time_period_days)
        
        return patterns
        
    except Exception as e:
        logger.error(f"Error analyzing historical patterns: {e}")
        return {
            "pattern_type": pattern_type,
            "error": str(e),
            "analysis_timestamp": datetime.now().isoformat()
        }


def _extract_search_terms(query: str) -> List[str]:
    """Extract key search terms from a query"""
    # Common DevOps/SRE terms
    devops_terms = [
        "error", "failure", "issue", "bug", "problem", "outage", "downtime",
        "performance", "latency", "timeout", "connection", "database", "server",
        "service", "api", "deployment", "release", "rollback", "monitoring",
        "alert", "cpu", "memory", "disk", "network", "load", "scaling",
        "kubernetes", "docker", "container", "pod", "namespace", "cluster",
        "nginx", "apache", "mysql", "postgresql", "redis", "kafka", "elk",
        "prometheus", "grafana", "jenkins", "git", "aws", "gcp", "azure"
    ]
    
    # Extract terms from query
    terms = []
    words = re.findall(r'\b\w+\b', query.lower())
    
    for word in words:
        if len(word) > 3:  # Include longer words
            terms.append(word)
    
    # Add recognized DevOps terms
    for term in devops_terms:
        if term in query.lower():
            terms.append(term)
    
    return list(set(terms))


def _search_incidents_comprehensive(terms: List[str], limit: int) -> List[Dict[str, Any]]:
    """Search incidents comprehensively"""
    try:
        incidents_df = load_incident_data()
        if incidents_df.empty:
            return []
        
        # Create search mask
        search_mask = pd.Series([False] * len(incidents_df))
        
        search_columns = ['u_symptom', 'short_description', 'description', 'category', 'subcategory', 'resolution']
        
        for term in terms:
            for col in search_columns:
                if col in incidents_df.columns:
                    mask = incidents_df[col].astype(str).str.contains(term, case=False, na=False)
                    search_mask = search_mask | mask
        
        filtered_df = incidents_df[search_mask].head(limit)
        return filtered_df.to_dict(orient='records')
        
    except Exception as e:
        logger.warning(f"Error searching incidents: {e}")
        return []


def _search_jira_issues_comprehensive(terms: List[str], limit: int) -> List[Dict[str, Any]]:
    """Search JIRA issues comprehensively"""
    try:
        jira_data = load_jira_data()
        issues_df = jira_data.get('issues', pd.DataFrame())
        
        if issues_df.empty:
            return []
        
        # Create search mask
        search_mask = pd.Series([False] * len(issues_df))
        
        search_columns = ['summary', 'description', 'status.name', 'priority.name', 'labels']
        
        for term in terms:
            for col in search_columns:
                if col in issues_df.columns:
                    mask = issues_df[col].astype(str).str.contains(term, case=False, na=False)
                    search_mask = search_mask | mask
        
        filtered_df = issues_df[search_mask].head(limit)
        return filtered_df.to_dict(orient='records')
        
    except Exception as e:
        logger.warning(f"Error searching JIRA issues: {e}")
        return []


def _search_jira_comments_comprehensive(terms: List[str], limit: int) -> List[Dict[str, Any]]:
    """Search JIRA comments comprehensively"""
    try:
        jira_data = load_jira_data()
        comments_df = jira_data.get('comments', pd.DataFrame())
        
        if comments_df.empty:
            return []
        
        # Create search mask
        search_mask = pd.Series([False] * len(comments_df))
        
        for term in terms:
            mask = comments_df['body'].astype(str).str.contains(term, case=False, na=False)
            search_mask = search_mask | mask
        
        filtered_df = comments_df[search_mask].head(limit)
        return filtered_df.to_dict(orient='records')
        
    except Exception as e:
        logger.warning(f"Error searching JIRA comments: {e}")
        return []


def _search_jira_changelog_comprehensive(terms: List[str], limit: int) -> List[Dict[str, Any]]:
    """Search JIRA changelog comprehensively"""
    try:
        jira_data = load_jira_data()
        changelog_df = jira_data.get('changelog', pd.DataFrame())
        
        if changelog_df.empty:
            return []
        
        # Create search mask
        search_mask = pd.Series([False] * len(changelog_df))
        
        search_columns = ['field', 'fromString', 'toString', 'authorDisplayName']
        
        for term in terms:
            for col in search_columns:
                if col in changelog_df.columns:
                    mask = changelog_df[col].astype(str).str.contains(term, case=False, na=False)
                    search_mask = search_mask | mask
        
        filtered_df = changelog_df[search_mask].head(limit)
        return filtered_df.to_dict(orient='records')
        
    except Exception as e:
        logger.warning(f"Error searching JIRA changelog: {e}")
        return []


def _analyze_results_for_answer(question: str, search_results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze search results to generate an answer"""
    evidence = []
    confidence = 0.0
    
    # Analyze incidents
    incidents = search_results["results"].get("incidents", [])
    for incident in incidents[:3]:  # Top 3 most relevant
        if incident.get("resolution"):
            evidence.append({
                "type": "incident",
                "id": incident.get("number"),
                "title": incident.get("short_description", ""),
                "resolution": incident.get("resolution", ""),
                "category": incident.get("category", "")
            })
            confidence += 0.2
    
    # Analyze JIRA issues
    jira_issues = search_results["results"].get("jira_issues", [])
    for issue in jira_issues[:3]:  # Top 3 most relevant
        if issue.get("resolution.name"):
            evidence.append({
                "type": "jira_issue",
                "id": issue.get("key"),
                "title": issue.get("summary", ""),
                "resolution": issue.get("resolution.name", ""),
                "status": issue.get("status.name", "")
            })
            confidence += 0.25
    
    # Analyze comments for solutions
    comments = search_results["results"].get("jira_comments", [])
    for comment in comments[:2]:  # Top 2 most relevant
        if len(comment.get("body", "")) > 50:  # Substantial comments
            evidence.append({
                "type": "jira_comment",
                "issue_key": comment.get("issue", ""),
                "author": comment.get("author", ""),
                "content": comment.get("body", "")[:200] + "..."
            })
            confidence += 0.15
    
    # Generate answer based on evidence
    if evidence:
        answer = f"Based on historical data, here are relevant solutions and insights:\n\n"
        
        for i, item in enumerate(evidence, 1):
            if item["type"] == "incident":
                answer += f"{i}. **Incident {item['id']}**: {item['title']}\n"
                answer += f"   - Resolution: {item['resolution']}\n"
                answer += f"   - Category: {item['category']}\n\n"
            elif item["type"] == "jira_issue":
                answer += f"{i}. **JIRA Issue {item['id']}**: {item['title']}\n"
                answer += f"   - Resolution: {item['resolution']}\n"
                answer += f"   - Status: {item['status']}\n\n"
            elif item["type"] == "jira_comment":
                answer += f"{i}. **Comment on {item['issue_key']}** by {item['author']}:\n"
                answer += f"   - {item['content']}\n\n"
    else:
        answer = "No specific solutions found in the knowledge base for this question."
        confidence = 0.0
    
    return {
        "answer": answer,
        "confidence": min(confidence, 1.0),
        "evidence": evidence
    }


def _generate_search_summary(results: Dict[str, Any]) -> str:
    """Generate a summary of search results"""
    total = results["total_results"]
    
    if total == 0:
        return "No results found in the knowledge base."
    
    summary = f"Found {total} relevant items across the knowledge base:\n"
    
    for source, items in results["results"].items():
        if items:
            summary += f"- {len(items)} {source.replace('_', ' ').title()}\n"
    
    return summary


def _analyze_incident_patterns(days: int) -> Dict[str, Any]:
    """Analyze incident patterns"""
    try:
        incidents_df = load_incident_data()
        if incidents_df.empty:
            return {"error": "No incident data available"}
        
        # Basic pattern analysis
        patterns = {
            "total_incidents": len(incidents_df),
            "categories": incidents_df['category'].value_counts().head(10).to_dict(),
            "priorities": incidents_df['priority'].value_counts().to_dict(),
            "states": incidents_df['incident_state'].value_counts().to_dict(),
            "assignment_groups": incidents_df['assignment_group'].value_counts().head(10).to_dict()
        }
        
        return patterns
        
    except Exception as e:
        return {"error": str(e)}


def _analyze_jira_patterns(days: int) -> Dict[str, Any]:
    """Analyze JIRA patterns"""
    try:
        jira_data = load_jira_data()
        issues_df = jira_data.get('issues', pd.DataFrame())
        
        if issues_df.empty:
            return {"error": "No JIRA data available"}
        
        # Basic pattern analysis
        patterns = {
            "total_issues": len(issues_df),
            "statuses": issues_df['status.name'].value_counts().head(10).to_dict(),
            "priorities": issues_df['priority.name'].value_counts().to_dict(),
            "issue_types": issues_df['issuetype.name'].value_counts().to_dict(),
            "projects": issues_df['project.key'].value_counts().head(10).to_dict()
        }
        
        return patterns
        
    except Exception as e:
        return {"error": str(e)}


def _analyze_failure_patterns(days: int) -> Dict[str, Any]:
    """Analyze failure patterns"""
    try:
        # Analyze high-priority incidents and critical JIRA issues
        incidents_df = load_incident_data()
        high_priority_incidents = incidents_df[incidents_df['priority'].str.contains('High|Critical', case=False, na=False)]
        
        jira_data = load_jira_data()
        issues_df = jira_data.get('issues', pd.DataFrame())
        critical_issues = issues_df[issues_df['priority.name'].str.contains('Critical|Highest', case=False, na=False)]
        
        patterns = {
            "high_priority_incidents": len(high_priority_incidents),
            "critical_jira_issues": len(critical_issues),
            "incident_categories": high_priority_incidents['category'].value_counts().head(5).to_dict(),
            "critical_issue_types": critical_issues['issuetype.name'].value_counts().head(5).to_dict()
        }
        
        return patterns
        
    except Exception as e:
        return {"error": str(e)} 
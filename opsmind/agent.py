import os
import sys
import logging
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

sys.path.append("..")
from callback_logging import log_query_to_model, log_model_response
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.langchain_tool import LangchainTool
from google.adk.tools.crewai_tool import CrewaiTool
from google.genai import types
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from crewai_tools import FileWriterTool

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
model_name = os.getenv("MODEL", "gemini-2.0-flash-001")

# Data loading functions
def load_incident_data():
    """Load incident data from CSV"""
    try:
        df = pd.read_csv("./data/incidents/incident_event_log.csv")
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
        issues_df = pd.read_csv("./data/jira/issues.csv")
        jira_data['issues'] = issues_df
        logger.info(f"Loaded {len(issues_df)} Jira issues")
        
        # Load Jira comments
        try:
            comments_df = pd.read_csv("./data/jira/comments.csv")
            jira_data['comments'] = comments_df
            logger.info(f"Loaded {len(comments_df)} Jira comments")
        except Exception as e:
            logger.warning(f"Could not load Jira comments: {e}")
            jira_data['comments'] = pd.DataFrame()
        
        # Load Jira changelog
        try:
            changelog_df = pd.read_csv("./data/jira/changelog.csv")
            jira_data['changelog'] = changelog_df
            logger.info(f"Loaded {len(changelog_df)} Jira changelog entries")
        except Exception as e:
            logger.warning(f"Could not load Jira changelog: {e}")
            jira_data['changelog'] = pd.DataFrame()
            
        # Load Jira issue links
        try:
            issuelinks_df = pd.read_csv("./data/jira/issuelinks.csv")
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

# Tool definitions for the agents
def process_incident_stream(
    tool_context: ToolContext,
    incident_data: str
) -> dict[str, str]:
    """Process incident data and add to context for RAG"""
    try:
        incident_info = json.loads(incident_data)
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
) -> dict[str, str]:
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

def generate_postmortem_content(
    tool_context: ToolContext,
    incident_id: str
) -> dict[str, str]:
    """Generate postmortem content based on incident and Jira data"""
    try:
        # Get incident context data
        context_result = get_incident_context(tool_context, incident_id)
        
        if context_result["status"] != "success":
            return {"status": "error", "message": f"Failed to get context for incident {incident_id}"}
        
        relevant_context = context_result["context"]
        
        # Find specific incident data
        incident_data = None
        for item in relevant_context:
            if item.get("type") == "incident" and item.get("id") == incident_id:
                incident_data = item
                break
        
        # Collect related Jira data
        jira_issues = [item for item in relevant_context if item.get("type") == "jira_issue"]
        jira_comments = [item for item in relevant_context if item.get("type") == "jira_comment"]
        jira_changelog = [item for item in relevant_context if item.get("type") == "jira_changelog"]
        jira_links = [item for item in relevant_context if item.get("type") == "jira_link"]
        
        # Generate postmortem content
        postmortem_content = f"""# Incident Postmortem: {incident_id}

## Executive Summary
This postmortem analyzes incident {incident_id} based on available incident data and related Jira information.

## Incident Details
- **Incident ID**: {incident_id}
- **Date/Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Status**: {incident_data.get('state', 'Unknown') if incident_data else 'Data not found'}
- **Category**: {incident_data.get('category', 'Unknown') if incident_data else 'Data not found'}
- **Priority**: {incident_data.get('priority', 'Unknown') if incident_data else 'Data not found'}
- **Description**: {incident_data.get('short_description', 'No description available') if incident_data else 'Data not found'}

## Root Cause Analysis
"""
        
        if incident_data:
            postmortem_content += f"""
Based on the incident data:
- **Symptom**: {incident_data.get('symptom', 'Not specified')}
- **Resolution Code**: {incident_data.get('resolution', 'Not specified')}
- **Full Description**: {incident_data.get('description', 'No detailed description available')}
"""
        else:
            postmortem_content += f"""
Incident {incident_id} was not found in the available incident data. This postmortem is based on related information from the system.
"""

        postmortem_content += f"""

## Related Jira Issues
"""
        if jira_issues:
            for issue in jira_issues[:5]:  # Limit to top 5 most relevant
                postmortem_content += f"""
### {issue.get('key', 'Unknown')}
- **Summary**: {issue.get('summary', 'No summary')}
- **Status**: {issue.get('status', 'Unknown')}
- **Priority**: {issue.get('priority', 'Unknown')}
- **Assignee**: {issue.get('assignee', 'Unassigned')}
- **Description**: {issue.get('description', 'No description')[:200]}...
"""
        else:
            postmortem_content += "\nNo directly related Jira issues found in the current dataset.\n"

        postmortem_content += f"""

## Jira Comments & Discussions
"""
        if jira_comments:
            for comment in jira_comments[:3]:  # Limit to top 3 most relevant
                postmortem_content += f"""
**Issue**: {comment.get('issue_key', 'Unknown')}  
**Author**: {comment.get('author', 'Unknown')}  
**Date**: {comment.get('created', 'Unknown')}  
**Comment**: {comment.get('body', 'No content')[:300]}...

"""
        else:
            postmortem_content += "\nNo related Jira comments found in the current dataset.\n"

        postmortem_content += f"""

## Timeline & Changes
"""
        if jira_changelog:
            postmortem_content += "\n**Key Status Changes from Jira:**\n"
            for change in jira_changelog[:5]:  # Limit to top 5 most relevant
                postmortem_content += f"""
- **{change.get('created', 'Unknown date')}**: {change.get('field', 'Field')} changed from "{change.get('from_string', 'N/A')}" to "{change.get('to_string', 'N/A')}" by {change.get('author', 'Unknown')}
"""
        else:
            postmortem_content += "\nNo Jira changelog data found for related issues.\n"

        postmortem_content += f"""

## Issue Relationships
"""
        if jira_links:
            postmortem_content += "\n**Related Issue Links:**\n"
            for link in jira_links[:3]:  # Limit to top 3
                postmortem_content += f"""
- {link.get('source_key', 'Unknown')} {link.get('link_type', 'relates to')} {link.get('target_key', 'Unknown')}
"""
        else:
            postmortem_content += "\nNo issue links found in the current dataset.\n"

        postmortem_content += f"""

## Lessons Learned
Based on the available data and analysis:
- Review incident categorization and symptom documentation
- Ensure proper linkage between incidents and Jira tracking
- Consider improving data collection for future postmortem analysis

## Action Items
1. **Data Quality**: Improve incident data collection and Jira integration
2. **Process Review**: Ensure all incidents have proper Jira ticket tracking
3. **Documentation**: Enhance incident description and symptom recording
4. **Monitoring**: Implement better incident-to-issue correlation

## Recommendations
- Establish clearer incident-to-Jira workflow processes
- Improve data consistency across incident and issue tracking systems
- Regular review of incident patterns and Jira issue resolution times

---
*This postmortem was automatically generated from available incident and Jira data on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*
"""
        
        return {
            "status": "success",
            "incident_id": incident_id,
            "content": postmortem_content,
            "message": f"Generated postmortem content for incident {incident_id}"
        }
        
    except Exception as e:
        logger.error(f"Error generating postmortem content: {e}")
        return {"status": "error", "message": str(e)}

def save_postmortem(
    tool_context: ToolContext,
    incident_id: str,
    postmortem_content: str
) -> dict[str, str]:
    """Save postmortem to markdown file and return content for display"""
    try:
        output_dir = Path("./output")
        output_dir.mkdir(exist_ok=True)
        
        filename = f"postmortem_{incident_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(postmortem_content)
        
        logger.info(f"Saved postmortem to {filepath}")
        return {
            "status": "success", 
            "filepath": str(filepath),
            "filename": filename,
            "content": postmortem_content,
            "message": f"Postmortem saved to {filename} and ready for display"
        }
    except Exception as e:
        logger.error(f"Error saving postmortem: {e}")
        return {"status": "error", "message": str(e)}

def list_postmortem_files(
    tool_context: ToolContext,
    show_content: bool = False
) -> dict[str, Any]:
    """List existing postmortem files and optionally show their content"""
    try:
        output_dir = Path("./output")
        if not output_dir.exists():
            return {"status": "success", "files": [], "message": "No postmortem files found - output directory doesn't exist yet"}
        
        postmortem_files = list(output_dir.glob("postmortem_*.md"))
        files_info = []
        
        for filepath in sorted(postmortem_files, key=lambda x: x.stat().st_mtime, reverse=True):
            file_info = {
                "filename": filepath.name,
                "filepath": str(filepath),
                "size": filepath.stat().st_size,
                "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
            }
            
            if show_content:
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_info["content"] = f.read()
            
            files_info.append(file_info)
        
        return {
            "status": "success",
            "files": files_info,
            "count": len(files_info),
            "message": f"Found {len(files_info)} postmortem files"
        }
    except Exception as e:
        logger.error(f"Error listing postmortem files: {e}")
        return {"status": "error", "message": str(e)}

def get_incident_context(
    tool_context: ToolContext,
    query: str
) -> dict[str, Any]:
    """Get incident context for RAG-based queries with enhanced Jira data"""
    try:
        # Load data if not already in state
        if "incident_memory" not in tool_context.state:
            incident_df = load_incident_data()
            jira_data = load_jira_data()
            
            # Create simple context from incident data
            incident_context = []
            for _, row in incident_df.head(100).iterrows():  # Limit for MVP
                context_entry = {
                    "type": "incident",
                    "id": row.get("number", "unknown"),
                    "state": row.get("incident_state", "unknown"),
                    "category": row.get("category", "unknown"),
                    "symptom": row.get("u_symptom", "unknown"),
                    "priority": row.get("priority", "unknown"),
                    "resolution": row.get("closed_code", "unknown"),
                    "short_description": row.get("short_description", "unknown"),
                    "description": row.get("description", "unknown")
                }
                incident_context.append(context_entry)
            
            # Enhanced Jira context with multiple data sources
            jira_context = []
            
            # Process Jira issues
            issues_df = jira_data.get('issues', pd.DataFrame())
            for _, row in issues_df.head(100).iterrows():  # Limit for MVP
                context_entry = {
                    "type": "jira_issue",
                    "key": row.get("key", "unknown"),
                    "summary": row.get("summary", "unknown"),
                    "priority": row.get("priority.name", "unknown"),
                    "status": row.get("status.name", "unknown"),
                    "resolution": row.get("resolution.description", "unknown"),
                    "description": row.get("description", "unknown"),
                    "assignee": row.get("assignee.displayName", "unknown"),
                    "reporter": row.get("reporter.displayName", "unknown"),
                    "created": row.get("created", "unknown"),
                    "updated": row.get("updated", "unknown")
                }
                jira_context.append(context_entry)
            
            # Process Jira comments
            comments_df = jira_data.get('comments', pd.DataFrame())
            for _, row in comments_df.head(50).iterrows():  # Limit comments
                context_entry = {
                    "type": "jira_comment",
                    "issue_key": row.get("issue_key", "unknown"),
                    "author": row.get("author.displayName", "unknown"),
                    "body": row.get("body", "unknown"),
                    "created": row.get("created", "unknown"),
                    "updated": row.get("updated", "unknown")
                }
                jira_context.append(context_entry)
            
            # Process Jira changelog
            changelog_df = jira_data.get('changelog', pd.DataFrame())
            for _, row in changelog_df.head(50).iterrows():  # Limit changelog
                context_entry = {
                    "type": "jira_changelog",
                    "issue_key": row.get("issue_key", "unknown"),
                    "author": row.get("author.displayName", "unknown"),
                    "field": row.get("field", "unknown"),
                    "from_string": row.get("fromString", "unknown"),
                    "to_string": row.get("toString", "unknown"),
                    "created": row.get("created", "unknown")
                }
                jira_context.append(context_entry)
            
            # Process Jira issue links
            issuelinks_df = jira_data.get('issuelinks', pd.DataFrame())
            for _, row in issuelinks_df.head(50).iterrows():  # Limit links
                context_entry = {
                    "type": "jira_link",
                    "source_key": row.get("sourceIssueKey", "unknown"),
                    "target_key": row.get("targetIssueKey", "unknown"),
                    "link_type": row.get("linkType.name", "unknown"),
                    "direction": row.get("linkType.inward", "unknown")
                }
                jira_context.append(context_entry)
            
            # Combine all context
            all_context = incident_context + jira_context
            tool_context.state["incident_memory"] = all_context
            logger.info(f"Loaded {len(incident_context)} incidents and {len(jira_context)} Jira items into memory")
        
        # Enhanced context search based on query keywords
        context = tool_context.state["incident_memory"]
        relevant_context = []
        
        query_lower = query.lower()
        query_keywords = query_lower.split()
        
        for item in context:
            item_text = str(item).lower()
            # Score relevance based on keyword matches
            matches = sum(1 for keyword in query_keywords if keyword in item_text)
            if matches > 0:
                item_with_score = item.copy()
                item_with_score["relevance_score"] = matches
                relevant_context.append(item_with_score)
        
        # Sort by relevance score and return top results
        relevant_context.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return {
            "status": "success",
            "context": relevant_context[:15],  # Return top 15 most relevant items
            "total_found": len(relevant_context),
            "jira_enabled": True,
            "data_sources": ["incidents", "jira_issues", "jira_comments", "jira_changelog", "jira_links"]
        }
    except Exception as e:
        logger.error(f"Error getting incident context: {e}")
        return {"status": "error", "message": str(e)}

# Agent Definitions

# 1. Listener Agent - Watches incident data
listener_agent = Agent(
    name="listener_agent",
    model=model_name,
    description="Watch incident log entries and emit structured events",
    instruction="""
    You are the Listener Agent for OpsMind. Your role is to:
    1. Process incoming incident data from CSV files
    2. Structure incident information into consistent format
    3. Emit structured events for downstream processing
    
    When processing incidents, extract key information:
    - Incident ID/Number
    - State/Status
    - Category and subcategory  
    - Symptoms and description
    - Priority and impact
    - Assignment group
    - Resolution information
    
    Use the process_incident_stream tool to add incidents to the processing pipeline.
    """,
    tools=[process_incident_stream]
)

# 2. Synthesizer Agent - RAG-based analysis with enhanced Jira integration
synthesizer_agent = Agent(
    name="synthesizer_agent", 
    model=model_name,
    description="Convert incident data into summaries using RAG context with full Jira integration",
    instruction="""
    You are the Synthesizer Agent for OpsMind. Your role is to:
    1. Analyze new incident data using historical context from incidents AND comprehensive Jira data
    2. Generate comprehensive incident summaries leveraging Jira issues, comments, changelog, and links
    3. Identify patterns and similarities with past incidents and related Jira tickets
    4. Provide context-aware insights using all available data sources
    
    You now have access to enhanced Jira data including:
    - Jira Issues: Full issue details, status, priority, assignee, reporter
    - Jira Comments: Discussion threads and resolution notes
    - Jira Changelog: History of field changes and status transitions
    - Jira Issue Links: Relationships between issues (blocks, relates to, etc.)
    
    Use the get_incident_context tool to search for relevant past incidents and comprehensive Jira data.
    Use the create_incident_summary tool to store your analysis.
    
    For each incident, provide:
    - Clear summary of what happened
    - Severity assessment based on similar Jira issues
    - Related Jira tickets with relevant comments and discussions
    - Timeline analysis using Jira changelog data
    - Linked issues that might provide additional context
    - Recommended resolution approach based on successful Jira resolutions
    - Key lessons learned from historical incident and Jira data
    """,
    tools=[get_incident_context, create_incident_summary]
)

# 3. Writer Agent - Generate postmortems with Jira insights
writer_agent = Agent(
    name="writer_agent",
    model=model_name,
    description="Generate comprehensive markdown postmortems from incident summaries with Jira data integration",
    instruction="""
    You are the Writer Agent for OpsMind. Your role is to:
    1. Take incident summaries and create detailed postmortem documents enriched with Jira data
    2. Structure postmortems in a clear, professional format with Jira ticket references
    3. Include root cause analysis, timeline, and action items based on comprehensive data
    4. Save documents in markdown format AND display them in chat
    5. Provide download information for the saved files
    
    **WORKFLOW for generating postmortems:**
    1. First, use generate_postmortem_content to create the postmortem content based on incident and Jira data
    2. Then, use save_postmortem with the generated content to save it to a file
    
    After saving the postmortem:
    1. Display the full postmortem content in your response
    2. Mention the filename and location where it was saved
    3. Let the user know the file is available for download
    
    The generate_postmortem_content tool will automatically create a comprehensive postmortem with these sections:
    - Executive Summary
    - Incident Details
    - Root Cause Analysis  
    - Related Jira Issues
    - Jira Comments & Discussions
    - Timeline & Changes
    - Issue Relationships
    - Lessons Learned
    - Action Items
    - Recommendations
    
    Always end your response by displaying the complete postmortem content and providing download information.
    """,
    tools=[generate_postmortem_content, save_postmortem]
)

# OpsMind Processing Pipeline
opsmind_pipeline = SequentialAgent(
    name="opsmind_pipeline",
    description="Complete incident-to-insight processing pipeline with enhanced Jira integration",
    sub_agents=[listener_agent, synthesizer_agent, writer_agent]
)

# Root Agent - Entry point with enhanced Jira capabilities
root_agent = Agent(
    name="opsmind",
    model=model_name,
    description="OpsMind - Autonomous Incident-to-Insight Assistant with Full Jira Integration",
    instruction="""
    Welcome to OpsMind - your autonomous incident-to-insight assistant with comprehensive Jira integration!
    
    🔍 **Enhanced Data Sources:**
    - Incident logs and historical data
    - Jira Issues (full details, status, priority, assignee)
    - Jira Comments (discussions and resolution notes)
    - Jira Changelog (field changes and status transitions)
    - Jira Issue Links (relationships between tickets)
    
    I can help you with:
    - Processing incident logs and learning from comprehensive historical data
    - Analyzing incidents using Jira tickets, comments, and change history
    - Generating detailed postmortem documents (displayed in chat + saved as files)
    - Identifying patterns across incidents and Jira data
    - Finding related Jira tickets and their resolution patterns
    
    🚨 **CRITICAL: When asked to create/generate a postmortem for an incident:**
    - IMMEDIATELY start generating the postmortem using available incident and Jira data
    - DO NOT ask the user if they have postmortem content - always use the available data
    - WORKFLOW: First use generate_postmortem_content to create the content, then use save_postmortem to save it
    - Use get_incident_context to retrieve relevant incident and Jira information if needed
    - Use create_incident_summary to analyze the incident if needed
    - Always be proactive and generate content from available data sources
    
    You can ask me to:
    1. "Process recent incidents" - I'll analyze incident data with full Jira context
    2. "Summarize incident [ID]" - I'll create a summary using related Jira data
    3. "Generate postmortem for [ID]" - I'll AUTOMATICALLY create a comprehensive postmortem with Jira insights using available data
    4. "List postmortems" or "Show existing postmortem files"
    5. "Show postmortem [filename]" - Display specific postmortem content
    6. Advanced queries like:
       - "What Jira tickets are related to database incidents?"
       - "Show me comment patterns in critical Jira issues"
       - "Find incidents linked to specific Jira ticket types"
       - "What's the resolution timeline for P1 issues based on Jira changelog?"
       - "Generate a postmortem including related Jira ticket discussions"
    
    🎯 **Enhanced RAG Capabilities:**
    I use Retrieval-Augmented Generation over your complete incident and Jira history including:
    - Issue descriptions and summaries
    - Comment threads and discussions
    - Status change history
    - Issue relationships and dependencies
    
    📋 **Postmortem Features:**
    - ✅ Full content displayed in chat for immediate review
    - 📁 Saved as markdown file in ./output/ directory
    - 💾 File available for download with timestamp-based filename
    - 🔗 Includes relevant Jira ticket references and insights
    - 📊 Timeline analysis using Jira changelog data
    
    What would you like me to help you with today?
    """,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    sub_agents=[opsmind_pipeline],
    tools=[get_incident_context, process_incident_stream, create_incident_summary, generate_postmortem_content, save_postmortem, list_postmortem_files]
) 
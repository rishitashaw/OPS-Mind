"""
Incident processing tools for OpsMind
"""
import json
import pandas as pd
from datetime import datetime
from typing import Any
from google.adk.tools.tool_context import ToolContext
from ..config import logger

def safe_json_loads(incident_data: str) -> Any:
    """Safely load JSON data with NaN handling"""
    try:
        # First attempt to load JSON normally
        data = json.loads(incident_data)
        
        # Clean any NaN values that might have slipped through
        def clean_nan_values(obj):
            if isinstance(obj, dict):
                return {k: clean_nan_values(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_nan_values(v) for v in obj]
            elif pd.isna(obj) or str(obj).lower() == 'nan':
                return "unknown"
            else:
                return obj
        
        return clean_nan_values(data)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        logger.error(f"Problematic JSON data: {incident_data[:200]}...")
        raise e

def process_incident_stream(
    tool_context: ToolContext,
    incident_data: str
) -> dict[str, str]:
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
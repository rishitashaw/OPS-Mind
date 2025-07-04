"""
Incident processing tools for OpsMind
"""
from datetime import datetime
from typing import Any, Dict

from google.adk.tools.tool_context import ToolContext
from opsmind.config import logger
from opsmind.utils import safe_json_loads

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
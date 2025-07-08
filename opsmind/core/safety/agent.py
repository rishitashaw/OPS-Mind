"""
Safety monitoring agent for OpsMind - MVP Version
"""

from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext
from opsmind.config import logger
from opsmind.tools.guardrail import monitor_safety_status, check_system_health

safety_agent = Agent(
    name="safety_agent",
    model="gemini-2.0-flash-thinking-exp",
    description="Safety monitoring for OpsMind",
    instruction="""
    You are a basic safety monitoring agent for OpsMind.
    Your job is to monitor guardrails and system health.
    
    Available tools:
    - monitor_safety_status: Check guardrails status
    - check_system_health: Check system resources
    
    Keep responses brief and focused.
    """,
    tools=[monitor_safety_status, check_system_health]
) 
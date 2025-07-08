"""
Safety and Guardrail Tools for OpsMind - Clean MVP Version
"""

from typing import Dict, Any
from google.adk.tools.tool_context import ToolContext
from opsmind.config import logger
from opsmind.core.safety import (
    get_guardrail_manager, 
    initialize_default_guardrails,
)


# === CORE MONITORING FUNCTIONS ===

def check_guardrails_health(tool_context: ToolContext) -> Dict[str, Any]:
    """Check comprehensive status of all guardrails"""
    try:
        manager = get_guardrail_manager()
        
        if not manager.guardrails:
            initialize_default_guardrails()
        
        stats = manager.get_stats()
        
        # Get rate limiter status
        rate_status = "not_configured"
        rate_limiter = manager.guardrails.get('rate_limiter')
        if rate_limiter and hasattr(rate_limiter, 'request_times'):
            current_requests = len(getattr(rate_limiter, 'request_times', []))
            max_requests = getattr(rate_limiter, 'max_requests', 0)
            rate_status = f"{current_requests}/{max_requests}"
        
        return {
            "status": "success",
            "total_guardrails": stats["total_guardrails"],
            "enabled_guardrails": stats["enabled_guardrails"],
            "guardrail_checks": stats["guardrail_checks"],
            "rate_limits": rate_status,
            "safety_status": "healthy" if stats["enabled_guardrails"] > 0 else "no_guardrails",
            "message": f"Health check complete. {stats['enabled_guardrails']} guardrails enabled."
        }
        
    except Exception as e:
        logger.error(f"Error checking guardrails health: {e}")
        return {
            "status": "error",
            "message": f"Failed to check guardrails health: {str(e)}"
        }


def get_system_resources(tool_context: ToolContext) -> Dict[str, Any]:
    """Get system resource information"""
    try:
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        resources = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "available_memory": memory.available,
            "total_memory": memory.total,
            "status": "healthy" if cpu_percent < 80 and memory.percent < 80 else "high_usage"
        }
        
        return {
            "status": "success",
            "resources": resources,
            "message": f"System: CPU {cpu_percent}%, Memory {memory.percent}%"
        }
        
    except Exception as e:
        logger.error(f"Error getting system resources: {e}")
        return {
            "status": "error",
            "message": f"Failed to get system resources: {str(e)}"
        }


# === CORE VALIDATION FUNCTIONS ===

def validate_input(tool_context: ToolContext, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input data through all guardrails"""
    try:
        manager = get_guardrail_manager()
        
        if not manager.guardrails:
            initialize_default_guardrails()
        
        # Create validation context
        context = {
            'function_name': 'validate_input',
            'data': data
        }
        
        # Run validation
        import asyncio
        result = asyncio.run(manager.check_all(context))
        
        return {
            'status': 'success',
            'validation_result': result['status'],
            'passed': result['passed'],
            'failed': result['failed'],
            'errors': result['errors'],
            'safe': result['status'] == 'allowed',
            'message': f"Input validation: {result['status']} - {result['passed']} passed, {result['failed']} failed"
        }
        
    except Exception as e:
        logger.error(f"Error validating input: {e}")
        return {
            'status': 'error',
            'safe': False,
            'message': f"Input validation failed: {str(e)}"
        }


def escape_ui_content(tool_context: ToolContext, content: str) -> Dict[str, Any]:
    """Escape content for safe UI display"""
    try:
        manager = get_guardrail_manager()
        
        if not manager.guardrails:
            initialize_default_guardrails()
        
        # Create escaping context
        context = {
            'function_name': 'escape_ui_content',
            'data': {'content': content}
        }
        
        # Run escaping
        import asyncio
        result = asyncio.run(manager.check_all(context))
        
        escaped_content = context['data']['content']
        was_modified = escaped_content != content
        
        return {
            'status': 'success',
            'original_content': content,
            'escaped_content': escaped_content,
            'was_modified': was_modified,
            'safe': True,
            'message': f"UI content {'escaped' if was_modified else 'safe'}"
        }
        
    except Exception as e:
        logger.error(f"Error escaping UI content: {e}")
        return {
            'status': 'error',
            'original_content': content,
            'escaped_content': content,
            'safe': False,
            'message': f"UI content escaping failed: {str(e)}"
        }


# === SETUP FUNCTION ===

def initialize_guardrails(tool_context: ToolContext) -> Dict[str, Any]:
    """Initialize the guardrail system"""
    try:
        initialize_default_guardrails()
        manager = get_guardrail_manager()
        
        stats = manager.get_stats()
        
        return {
            "status": "success",
            "initialized_guardrails": stats["total_guardrails"],
            "enabled_guardrails": stats["enabled_guardrails"],
            "types": ["validation", "rate_limiting", "ui_content_escaping"],
            "message": f"Initialized {stats['total_guardrails']} guardrails successfully"
        }
        
    except Exception as e:
        logger.error(f"Error initializing guardrails: {e}")
        return {
            "status": "error",
            "message": f"Failed to initialize guardrails: {str(e)}"
        }


# === SIMPLIFIED AGENT HELPERS ===

def monitor_safety_status(tool_context: ToolContext) -> str:
    """Simple safety status for agent use"""
    try:
        result = check_guardrails_health(tool_context)
        
        if result['status'] == 'success':
            return f"Safety: {result['enabled_guardrails']} guardrails enabled - {result['safety_status']}"
        else:
            return f"Safety check failed: {result['message']}"
        
    except Exception as e:
        logger.error(f"Error monitoring safety: {e}")
        return f"Safety monitoring error: {str(e)}"


def check_system_health(tool_context: ToolContext) -> str:
    """Simple system health for agent use"""
    try:
        result = get_system_resources(tool_context)
        
        if result['status'] == 'success':
            resources = result['resources']
            return f"System: CPU {resources['cpu_percent']}%, Memory {resources['memory_percent']}% - {resources['status']}"
        else:
            return f"System check failed: {result['message']}"
        
    except Exception as e:
        logger.error(f"Error checking system health: {e}")
        return f"System health check error: {str(e)}" 
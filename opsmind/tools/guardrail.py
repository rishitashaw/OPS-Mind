"""
Guardrail management tools for OpsMind agents
"""

from typing import Dict, Any
from google.adk.tools.tool_context import ToolContext
from opsmind.config import logger
from opsmind.core.safety import (
    get_guardrail_manager, 
    initialize_default_guardrails,
    GuardrailConfig,
    GuardrailType
)


def check_guardrails_health(tool_context: ToolContext) -> Dict[str, Any]:
    """Check the health status of all guardrails"""
    try:
        manager = get_guardrail_manager()
        
        # Initialize default guardrails if none exist
        if not manager.guardrails:
            initialize_default_guardrails()
        
        health_report = manager.get_health_report()
        stats = manager.get_stats()
        
        return {
            "status": "success",
            "health_report": health_report,
            "stats": stats,
            "message": f"Guardrails health check complete. Status: {health_report['status']}"
        }
        
    except Exception as e:
        logger.error(f"Error checking guardrails health: {e}")
        return {
            "status": "error",
            "message": f"Failed to check guardrails health: {str(e)}"
        }


def get_guardrail_stats(tool_context: ToolContext) -> Dict[str, Any]:
    """Get detailed statistics for all guardrails"""
    try:
        manager = get_guardrail_manager()
        
        if not manager.guardrails:
            initialize_default_guardrails()
        
        stats = manager.get_stats()
        
        # Add summary information
        summary = {
            "total_guardrails": stats["total_guardrails"],
            "enabled_guardrails": stats["enabled_guardrails"],
            "recent_executions": stats["recent_executions"],
            "overall_health": "healthy" if stats["enabled_guardrails"] > 0 else "no_guardrails"
        }
        
        return {
            "status": "success",
            "summary": summary,
            "detailed_stats": stats,
            "message": f"Retrieved stats for {stats['total_guardrails']} guardrails"
        }
        
    except Exception as e:
        logger.error(f"Error getting guardrail stats: {e}")
        return {
            "status": "error",
            "message": f"Failed to get guardrail stats: {str(e)}"
        }


def initialize_guardrails(tool_context: ToolContext) -> Dict[str, Any]:
    """Initialize default guardrails for the system"""
    try:
        initialize_default_guardrails()
        manager = get_guardrail_manager()
        
        stats = manager.get_stats()
        
        return {
            "status": "success",
            "initialized_guardrails": stats["total_guardrails"],
            "enabled_guardrails": stats["enabled_guardrails"],
            "message": f"Initialized {stats['total_guardrails']} default guardrails"
        }
        
    except Exception as e:
        logger.error(f"Error initializing guardrails: {e}")
        return {
            "status": "error",
            "message": f"Failed to initialize guardrails: {str(e)}"
        }


def test_guardrails(tool_context: ToolContext, test_data: str = "{}") -> Dict[str, Any]:
    """Test guardrails with sample data"""
    try:
        import json
        import asyncio
        
        manager = get_guardrail_manager()
        
        if not manager.guardrails:
            initialize_default_guardrails()
        
        # Parse test data
        try:
            data = json.loads(test_data)
        except json.JSONDecodeError:
            data = {"test": "sample data"}
        
        # Create test context
        context = {
            "function_name": "test_function",
            "agent_name": "test",
            "data": data
        }
        
        # Run guardrails check
        async def run_test():
            return await manager.check_all(context, "test")
        
        # Execute the test
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, run_test())
                    result = future.result(timeout=30)
            else:
                result = asyncio.run(run_test())
        except Exception as e:
            # Fallback for sync execution
            result = {"status": "error", "message": f"Could not run async test: {str(e)}"}
        
        return {
            "status": "success",
            "test_result": result,
            "message": f"Guardrails test completed. Status: {result.get('status', 'unknown')}"
        }
        
    except Exception as e:
        logger.error(f"Error testing guardrails: {e}")
        return {
            "status": "error",
            "message": f"Failed to test guardrails: {str(e)}"
        }


def configure_guardrail(
    tool_context: ToolContext,
    name: str,
    guardrail_type: str,
    enabled: bool = True,
    strict_mode: bool = False,
    custom_params: str = "{}"
) -> Dict[str, Any]:
    """Configure a specific guardrail"""
    try:
        import json
        
        manager = get_guardrail_manager()
        
        # Parse custom parameters
        try:
            params = json.loads(custom_params)
        except json.JSONDecodeError:
            params = {}
        
        # Map string type to enum
        type_mapping = {
            "validation": GuardrailType.VALIDATION,
            "rate_limiting": GuardrailType.RATE_LIMITING,
            "circuit_breaker": GuardrailType.CIRCUIT_BREAKER,
            "resource_monitor": GuardrailType.RESOURCE_MONITOR,
            "data_sanitization": GuardrailType.DATA_SANITIZATION,
            "ui_content_escaping": GuardrailType.UI_CONTENT_ESCAPING
        }
        
        if guardrail_type not in type_mapping:
            return {
                "status": "error",
                "message": f"Unknown guardrail type: {guardrail_type}. Available types: {list(type_mapping.keys())}"
            }
        
        # Create configuration
        config = GuardrailConfig(
            name=name,
            type=type_mapping[guardrail_type],
            enabled=enabled,
            strict_mode=strict_mode,
            custom_params=params
        )
        
        # Add or update guardrail
        success = manager.add_guardrail(config)
        
        if success:
            return {
                "status": "success",
                "guardrail_name": name,
                "guardrail_type": guardrail_type,
                "enabled": enabled,
                "strict_mode": strict_mode,
                "message": f"Successfully configured guardrail: {name}"
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to configure guardrail: {name}"
            }
        
    except Exception as e:
        logger.error(f"Error configuring guardrail: {e}")
        return {
            "status": "error",
            "message": f"Failed to configure guardrail: {str(e)}"
        }


def get_system_resources(tool_context: ToolContext) -> Dict[str, Any]:
    """Get current system resource usage"""
    try:
        import psutil
        
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        
        # Get process info
        process = psutil.Process()
        
        resources = {
            "cpu_percent": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            },
            "process": {
                "pid": process.pid,
                "memory_percent": process.memory_percent(),
                "num_threads": process.num_threads(),
                "open_files": len(process.open_files()) if hasattr(process, 'open_files') else 0
            }
        }
        
        return {
            "status": "success",
            "resources": resources,
            "message": f"System resources retrieved. CPU: {cpu_percent}%, Memory: {memory.percent}%"
        }
        
    except Exception as e:
        logger.error(f"Error getting system resources: {e}")
        return {
            "status": "error",
            "message": f"Failed to get system resources: {str(e)}"
        } 
"""
Compatibility layer for ADK framework
This module maintains backward compatibility while using the new modular structure
"""

# Import the root_agent from our new modular structure
from .core.agents import root_agent

# Export for ADK framework compatibility
__all__ = ['root_agent'] 
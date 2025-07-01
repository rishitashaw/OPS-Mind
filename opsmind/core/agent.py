"""
Main entry point for OpsMind agent
"""
import sys
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from ..utils.logging import log_query_to_model, log_model_response
from .agents import root_agent

# Export the main agent
__all__ = ['root_agent'] 
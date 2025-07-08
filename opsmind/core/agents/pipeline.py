"""
Pipeline Agent for OpsMind - Complete incident-to-insight processing pipeline
"""
from google.adk.agents import SequentialAgent

from opsmind.core.safety import safety_agent

from .listener import listener
from .synthesizer import synthesizer
from .writer import writer

# OpsMind Processing Pipeline
pipeline = SequentialAgent(
    name="pipeline",
    description="Complete incident-to-insight processing pipeline with enhanced Jira integration",
    sub_agents=[safety_agent, listener, synthesizer, writer]
) 
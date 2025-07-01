"""
Pipeline Agent for OpsMind - Complete incident-to-insight processing pipeline
"""
from google.adk.agents import SequentialAgent
from .listener_agent import listener_agent
from .synthesizer_agent import synthesizer_agent
from .writer_agent import writer_agent

# OpsMind Processing Pipeline
opsmind_pipeline = SequentialAgent(
    name="opsmind_pipeline",
    description="Complete incident-to-insight processing pipeline with enhanced Jira integration",
    sub_agents=[listener_agent, synthesizer_agent, writer_agent]
) 
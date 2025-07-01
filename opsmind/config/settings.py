"""
Configuration and setup for OpsMind
"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Model configuration
MODEL_NAME = os.getenv("MODEL", "gemini-2.0-flash-001")

# Data paths
INCIDENT_DATA_PATH = "./opsmind/data/incidents/incident_event_log.csv"
JIRA_ISSUES_PATH = "./opsmind/data/jira/issues.csv"
JIRA_COMMENTS_PATH = "./opsmind/data/jira/comments.csv"
JIRA_CHANGELOG_PATH = "./opsmind/data/jira/changelog.csv"
JIRA_ISSUELINKS_PATH = "./opsmind/data/jira/issuelinks.csv"

# Output configuration
OUTPUT_DIR = "./output"

# Logging configuration
def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging() 
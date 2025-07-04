"""
Configuration settings for OpsMind
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Model configuration
MODEL_NAME = os.getenv("MODEL", "gemini-2.0-flash-001")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_GENAI_USE_VERTEXAI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").upper() == "TRUE"

# Jira connector configuration
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "")
JIRA_USERNAME = os.getenv("JIRA_USERNAME", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEYS = os.getenv("JIRA_PROJECT_KEYS", "").split(",") if os.getenv("JIRA_PROJECT_KEYS") else []
JIRA_POLL_INTERVAL = int(os.getenv("JIRA_POLL_INTERVAL", "300"))  # 5 minutes default
JIRA_BATCH_SIZE = int(os.getenv("JIRA_BATCH_SIZE", "100"))
JIRA_MAX_RETRIES = int(os.getenv("JIRA_MAX_RETRIES", "3"))
JIRA_RETRY_DELAY = int(os.getenv("JIRA_RETRY_DELAY", "5"))
JIRA_ENABLED = os.getenv("JIRA_ENABLED", "FALSE").upper() == "TRUE"

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "opsmind" / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Data file paths
INCIDENT_DATA_PATH = DATA_DIR / "datasets" / "incidents" / "incident_event_log.csv"
JIRA_ISSUES_PATH = DATA_DIR / "datasets" / "jira" / "issues.csv"
JIRA_COMMENTS_PATH = DATA_DIR / "datasets" / "jira" / "comments.csv"
JIRA_CHANGELOG_PATH = DATA_DIR / "datasets" / "jira" / "changelog.csv"
JIRA_ISSUELINKS_PATH = DATA_DIR / "datasets" / "jira" / "issuelinks.csv"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Preset configurations for different "moods"
PRESETS = {
    "quick": {
        "description": "Fast CSV-only queries",
        "config": {
            "csv_incidents": True,
            "csv_jira": False,
            "jira_stream": False
        }
    },
    "full": {
        "description": "All available sources",
        "config": {
            "csv_incidents": True,
            "csv_jira": True,
            "jira_stream": True
        }
    },
    "live": {
        "description": "Real-time data only",
        "config": {
            "csv_incidents": False,
            "csv_jira": False,
            "jira_stream": True
        }
    }
}

# Logging configuration
def setup_logging(level: str = "INFO") -> logging.Logger:
    """Setup logging configuration with consistent format"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(OUTPUT_DIR / "opsmind.log")
        ]
    )
    
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

# Configuration validation
def validate_config() -> bool:
    """Validate configuration settings"""
    valid = True
    
    if not GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set in environment")
        valid = False
    
    if not INCIDENT_DATA_PATH.exists():
        logger.warning(f"Incident data file not found: {INCIDENT_DATA_PATH}")
        valid = False
    
    if not JIRA_ISSUES_PATH.exists():
        logger.warning(f"Jira issues file not found: {JIRA_ISSUES_PATH}")
        valid = False
    
    # Validate Jira configuration if enabled
    if JIRA_ENABLED:
        if not JIRA_BASE_URL:
            logger.warning("JIRA_BASE_URL not set but Jira is enabled")
            valid = False
        if not JIRA_USERNAME:
            logger.warning("JIRA_USERNAME not set but Jira is enabled")
            valid = False
        if not JIRA_API_TOKEN:
            logger.warning("JIRA_API_TOKEN not set but Jira is enabled")
            valid = False
        if not JIRA_PROJECT_KEYS:
            logger.warning("JIRA_PROJECT_KEYS not set but Jira is enabled")
            valid = False
    
    if valid:
        logger.info("Configuration validation passed")
    else:
        logger.warning("Configuration validation completed with warnings")
    
    return valid


def get_jira_config() -> dict:
    """Get Jira connector configuration"""
    return {
        "base_url": JIRA_BASE_URL,
        "username": JIRA_USERNAME,
        "api_token": JIRA_API_TOKEN,
        "project_keys": JIRA_PROJECT_KEYS,
        "poll_interval": JIRA_POLL_INTERVAL,
        "batch_size": JIRA_BATCH_SIZE,
        "max_retries": JIRA_MAX_RETRIES,
        "retry_delay": JIRA_RETRY_DELAY,
        "enabled": JIRA_ENABLED
    }


# Export all configuration variables
__all__ = [
    "MODEL_NAME",
    "GOOGLE_API_KEY", 
    "GOOGLE_GENAI_USE_VERTEXAI",
    "JIRA_BASE_URL",
    "JIRA_USERNAME",
    "JIRA_API_TOKEN",
    "JIRA_PROJECT_KEYS",
    "JIRA_POLL_INTERVAL",
    "JIRA_BATCH_SIZE",
    "JIRA_MAX_RETRIES",
    "JIRA_RETRY_DELAY",
    "JIRA_ENABLED",
    "PROJECT_ROOT",
    "DATA_DIR",
    "OUTPUT_DIR",
    "INCIDENT_DATA_PATH",
    "JIRA_ISSUES_PATH",
    "JIRA_COMMENTS_PATH",
    "JIRA_CHANGELOG_PATH",
    "JIRA_ISSUELINKS_PATH",
    "logger",
    "setup_logging",
    "validate_config",
    "get_jira_config"
] 
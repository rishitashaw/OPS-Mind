# OpsMind - Autonomous Incident-to-Insight Assistant

OpsMind is an AI-powered incident management system built with Google's Agent Development Kit (ADK). It processes incident logs, learns from historical data, and automatically generates comprehensive postmortem documents.

## 🏗️ Architecture

OpsMind uses a **multi-agent system**:

1. **Listener Agent** - Watches incident logs and structures data
2. **Synthesizer Agent** - Uses RAG to analyze incidents with historical context  
3. **Writer Agent** - Generates markdown postmortem documents
4. **Pipeline Agent** - Orchestrates the flow between agents
5. **Root Agent** - Main user interface and entry point

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Google Cloud Project with Vertex AI enabled
- Google Cloud credentials configured

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify installation
python opsmind/tests/test_opsmind.py
```

### 2. Configuration

Configure your environment variables in `opsmind/config/settings.py` or set them directly:

```bash
export GOOGLE_API_KEY=YOUR_API_KEY
export GOOGLE_GENAI_USE_VERTEXAI=FALSE
export MODEL=gemini-2.0-flash-001
```

### 3. Run OpsMind

**Command Line Interface:**
```bash
adk run opsmind
```

**Web Interface:**
```bash
adk web
```

**Try the Example:**
```bash
python opsmind/examples/basic_usage.py
```

## 📊 Data Sources

OpsMind uses two datasets for RAG-based learning:

- **Incident Logs** (`opsmind/data/incidents/`) - IT incident event logs
- **Jira Issues** (`opsmind/data/jira/`) - Apache project Jira tickets

The system automatically downloads and processes these datasets on first run.

## 💬 Sample Prompts

Once OpsMind is running, try these prompts:

### Basic Operations
```
"Process recent incidents"
"Summarize incident INC0000045" 
"Generate postmortem for INC0000045"
```

### RAG-based Queries
```
"Summarize the incident where the database connection failed on March 12."

"What resolution pattern was used most frequently for 500 errors?"

"Compare two Jira tickets tagged with 'critical' — what's the common failure mode?"

"Generate a postmortem for the most recent incident involving Kubernetes pods."
```

## 🔧 Agent Details

### Listener Agent
- **Role**: Process incident streams
- **Input**: CSV incident data
- **Output**: Structured incident events
- **Tools**: `process_incident_stream`

### Synthesizer Agent  
- **Role**: RAG-based incident analysis
- **Input**: Incident events + historical context
- **Output**: Comprehensive summaries
- **Tools**: `get_incident_context`, `create_incident_summary`

### Writer Agent
- **Role**: Generate postmortem documents
- **Input**: Incident summaries
- **Output**: Markdown postmortems
- **Tools**: `save_postmortem`

### Pipeline Agent
- **Role**: Orchestrate agent workflows
- **Input**: User requests
- **Output**: Coordinated agent responses

### Root Agent
- **Role**: Main user interface
- **Input**: User queries
- **Output**: Delegated responses from specialized agents

## 📁 Project Structure

```
ops/
├── opsmind/                # Main agent system
│   ├── core/              # Core agent implementations
│   │   ├── agents/        # Individual agent definitions
│   │   │   ├── listener_agent.py
│   │   │   ├── synthesizer_agent.py
│   │   │   ├── writer_agent.py
│   │   │   ├── pipeline_agent.py
│   │   │   └── root_agent.py
│   │   ├── agents.py      # Agent imports
│   │   └── agent.py       # Main entry point
│   ├── tools/             # Tool functions
│   │   ├── context_tools.py
│   │   ├── incident_tools.py
│   │   └── postmortem_tools.py
│   ├── utils/             # Utility functions
│   │   └── logging.py
│   ├── config/            # Configuration
│   │   └── settings.py
│   ├── data/              # Training datasets
│   │   ├── incidents/     # IT incident logs
│   │   └── jira/         # Jira issues
│   ├── examples/          # Usage examples
│   │   └── basic_usage.py
│   ├── tests/             # Test suite
│   │   └── test_opsmind.py
│   ├── docs/              # Documentation
│   │   └── README.md
│   └── __init__.py
├── requirements.txt        # Dependencies
├── pyproject.toml         # Project configuration
├── Makefile              # Build automation
├── DEVELOPMENT.md        # Development guide
├── CHANGELOG.md          # Version history
└── README.md             # This file
```

## 🧪 Testing

Run the test suite to verify everything is working:

```bash
python opsmind/tests/test_opsmind.py
```

The tests verify:
- ✅ Data loading from CSV files
- ✅ Agent imports and initialization  
- ✅ Tool function execution
- ✅ Configuration setup

## 📋 Sample Output

OpsMind generates postmortem documents like this:

```markdown
# Incident Postmortem: INC0000045

## Executive Summary
Database connection failure affecting production services from 01:16 to 11:29.

## Incident Details
- **Incident ID**: INC0000045
- **Date/Time**: 29/2/2016 01:16
- **Duration**: ~10 hours  
- **Severity**: Medium Priority
- **Affected Systems**: Production Database

## Root Cause Analysis
Connection timeout due to network configuration changes...

## Timeline
- 01:16 - Initial incident reported
- 08:53 - Issue escalated to database team
- 11:29 - Resolution implemented

## Resolution
Network configuration was reverted to previous stable state...

## Lessons Learned
Based on similar past incidents, implement automated rollback procedures...

## Action Items
1. Implement database connection monitoring
2. Create automated failover procedures
3. Update runbook documentation
```

## 🔑 Key Features

- **RAG-powered Analysis**: Uses historical incident and Jira data for context
- **Automatic Postmortems**: Generates comprehensive markdown documents
- **Multi-Agent Architecture**: Specialized agents for different tasks
- **Local Processing**: No external APIs required beyond Google Cloud
- **Structured Pipeline**: Clear separation of concerns across agents
- **Extensible Design**: Easy to add new data sources and agents

## 🚧 Current Status

This is an active development project with these capabilities:

- Enhanced Jira integration (issues, comments, changelog, links)
- Multi-agent architecture with specialized roles
- RAG-based analysis using historical data
- File output with comprehensive postmortems
- Pattern recognition and insights

## 🔄 Usage Workflow

1. **Data Ingestion**: Listener Agent processes incident CSVs
2. **Analysis**: Synthesizer Agent applies RAG over historical data  
3. **Documentation**: Writer Agent creates markdown postmortems
4. **Orchestration**: Pipeline Agent coordinates the workflow
5. **Interface**: Root Agent provides user interaction

## 🤝 Contributing

To extend OpsMind:

1. Add new agent types in `opsmind/core/agents/`
2. Implement additional tools in `opsmind/tools/`
3. Enhance RAG capabilities
4. Add new data source integrations
5. Improve the user interface

## 📚 References

- [ADK Multi-Agent Systems Blog Post](https://bgiri-gcloud.medium.com/how-to-build-multi-agent-systems-with-adk-agent-development-kit-cd727ab00ba2)
- [Google Agent Development Kit](https://google.github.io/agent-development-kit/)
- [Agent2Agent Protocol](https://google-a2a.github.io/)

---

**OpsMind** - *From Incident to Insight, Autonomously* 🧠⚡ 
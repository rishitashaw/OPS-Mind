# OpsMind - Autonomous Incident-to-Insight Assistant

OpsMind is an AI-powered incident management system built with Google's Agent Development Kit (ADK). It processes incident logs, learns from historical data, and automatically generates comprehensive postmortem documents with enhanced Jira integration.

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

```

### 2. Data Setup

**⚠️ Important: Dataset Not Included in Repository**

Due to the large size of the datasets (8GB+ total), they are not included in this repository. You need to download them from Kaggle:

#### Download Required Datasets

1. **Incident Event Log Dataset**
   ```bash
   # Download from Kaggle
   kaggle datasets download shamiulislamshifat/it-incident-log-dataset
   # Extract to: opsmind/data/datasets/incidents/incident_event_log.csv
   ```

2. **Jira Issues Dataset**
   ```bash
   # Download from Kaggle
   kaggle datasets download tedlozzo/apaches-jira-issues
   # Extract to: opsmind/data/datasets/jira/
   # Files: issues.csv, comments.csv, changelog.csv, issuelinks.csv
   ```

#### Dataset Structure

After downloading, your data directory should look like:
```
opsmind/data/datasets/
├── incidents/
│   └── incident_event_log.csv    (44MB - IT incident logs)
└── jira/
    ├── issues.csv                (1.8GB - Jira issue details)
    ├── comments.csv              (3.8GB - Issue comments & discussions)
    ├── changelog.csv             (2.5GB - Field changes & status transitions)
    └── issuelinks.csv            (99MB - Issue relationships & dependencies)
```

### 3. Configuration

Configure your environment variables in `.env` file:

```bash
# Core Configuration
GOOGLE_API_KEY=your_google_api_key
GOOGLE_GENAI_USE_VERTEXAI=FALSE
MODEL=gemini-2.0-flash-001

# Jira Real-time Connector (Optional)
JIRA_ENABLED=FALSE
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_USERNAME=your-email@company.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEYS=PROJ1,PROJ2,PROJ3
JIRA_POLL_INTERVAL=300
```

### 4. Run OpsMind

**Command Line Interface:**
```bash
adk run opsmind
```

**Web Interface:**
```bash
adk web
```

**Validate Configuration:**
```bash
python -c "from opsmind.config import validate_config; validate_config()"
```

## 📊 Data Sources & Analytics

OpsMind leverages multiple data sources for comprehensive incident analysis:

### Static Data Sources (CSV)

1. **Incident Event Log** (44MB)
   - 141,712 incident records
   - Fields: ID, state, category, symptoms, priority, resolution
   - Time range: Real IT environment incident data
   - Use case: Historical incident pattern analysis

2. **Jira Issues Dataset** (1.8GB)
   - 500,000+ Jira issues from Apache projects
   - Fields: Summary, description, status, priority, assignee, components
   - Rich metadata: Labels, fix versions, custom fields
   - Use case: Issue resolution patterns and workflows

3. **Jira Comments** (3.8GB)
   - Millions of comments across issues
   - Discussion threads, resolution notes, updates
   - Author information and timestamps
   - Use case: Communication patterns and solution discovery

4. **Jira Changelog** (2.5GB)
   - Complete audit trail of issue changes
   - Status transitions, field updates, assignments
   - Historical workflow analysis
   - Use case: Process optimization and bottleneck identification

5. **Jira Issue Links** (99MB)
   - Dependencies, relationships, and connections
   - Link types: blocks, relates to, duplicates
   - Cross-project relationships
   - Use case: Impact analysis and dependency mapping

### Real-time Data Sources (Optional)

- **Live Jira Integration**: Real-time issue updates, comments, and status changes
- **Custom Connectors**: Extensible framework for additional data sources

### Data Processing Features

- **RAG-powered Analysis**: Semantic search across all data sources
- **Intelligent Filtering**: Context-aware data retrieval
- **Multi-source Correlation**: Links incidents with Jira issues
- **Pattern Recognition**: Identifies recurring issues and solutions
- **Automated Insights**: Generates actionable recommendations

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

"Find incidents with similar symptoms to JIRA-12345"

"What are the common causes of high-priority database incidents?"
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
- **Tools**: `generate_postmortem_content`, `save_postmortem`

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
├── opsmind/                    # Main OpsMind package
│   ├── config/                 # Configuration management
│   │   ├── __init__.py        # Config exports
│   │   └── settings.py        # Environment variables & validation
│   ├── core/                   # Core agent implementations
│   │   ├── agents/            # Individual agent definitions
│   │   │   ├── listener_agent.py      # Incident data processing
│   │   │   ├── synthesizer_agent.py   # RAG-based analysis
│   │   │   ├── writer_agent.py        # Postmortem generation
│   │   │   ├── pipeline_agent.py      # Agent orchestration
│   │   │   └── root_agent.py          # Main user interface
│   │   ├── __init__.py        # Core exports
│   │   └── agents.py          # Agent registry
│   ├── data/                   # Data management & loading
│   │   ├── connectors/        # Real-time data connectors
│   │   │   ├── base_connector.py      # Connector interface
│   │   │   ├── jira_connector.py      # Jira real-time connector
│   │   │   ├── connector_manager.py   # Multi-connector management
│   │   │   └── __init__.py            # Connector exports
│   │   ├── datasets/          # Data files (download from Kaggle)
│   │   │   ├── incidents/     # IT incident logs
│   │   │   │   └── incident_event_log.csv
│   │   │   └── jira/          # Jira project data
│   │   │       ├── issues.csv
│   │   │       ├── comments.csv
│   │   │       ├── changelog.csv
│   │   │       └── issuelinks.csv
│   │   ├── __init__.py        # Data exports
│   │   ├── loader.py          # CSV data loading functions
│   │   └── manager.py         # Unified data source management
│   ├── tools/                  # Agent tool functions
│   │   ├── context_tools.py   # RAG context retrieval
│   │   ├── context.py         # Unified data access interface
│   │   ├── incident_tools.py  # Incident processing tools
│   │   ├── postmortem_tools.py # Postmortem generation
│   │   ├── realtime.py        # Real-time data management
│   │   └── __init__.py        # Tool exports
│   ├── utils/                  # Utility functions
│   │   ├── data_helpers.py    # Data processing utilities
│   │   ├── logging.py         # Logging configuration
│   │   └── __init__.py        # Utils exports
│   ├── docs/                   # Documentation
│   │   └── README.md          # Detailed documentation
│   ├── __init__.py            # Main package entry
│   └── agent.py               # ADK compatibility layer
├── output/                     # Generated postmortems & logs
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Project configuration
├── Makefile                   # Development commands
├── DEVELOPMENT.md             # Development guide
├── CHANGELOG.md               # Version history
└── README.md                  # This file
```

## 🧪 Testing

Run the test suite to verify everything is working:

```bash
# Quick validation
python -c "
from opsmind.config import validate_config
from opsmind.data import validate_data_files
print('Config:', validate_config())
print('Data:', validate_data_files())
"

# Full test (if test files exist)
python opsmind/tests/test_opsmind.py
```

## 📋 Sample Output

OpsMind generates comprehensive postmortem documents:

```markdown
# Incident Postmortem: INC0000045

## Executive Summary
Database connection failure affecting production services from 01:16 to 11:29.
Analysis based on 127 similar incidents and 45 related Jira issues.

## Incident Details
- **Incident ID**: INC0000045
- **Date/Time**: 29/2/2016 01:16
- **Duration**: ~10 hours  
- **Severity**: Medium Priority
- **Affected Systems**: Production Database

## Root Cause Analysis
Connection timeout due to network configuration changes.
Pattern identified across 12 similar incidents in past 6 months.

## Related Jira Issues
- **INFRA-2341**: Database connectivity issues (Resolved)
- **NET-1156**: Network timeout configurations (In Progress)
- **MON-445**: Database monitoring improvements (Closed)

## Timeline
- 01:16 - Initial incident reported
- 02:30 - Escalated based on similar incident INC0000032
- 08:53 - Issue escalated to database team
- 11:29 - Resolution implemented using JIRA-2341 solution

## Resolution
Network configuration reverted to previous stable state.
Solution adapted from Jira issue INFRA-2341 comments.

## Lessons Learned
Based on analysis of 127 similar incidents:
- Implement automated rollback procedures (mentioned in 23 cases)
- Enhance monitoring (recommended in 67% of similar incidents)
- Update runbooks (action item in 45 related cases)

## Action Items
1. **Database Monitoring** - Implement connection health checks
2. **Automated Failover** - Based on patterns from JIRA-2341, INFRA-1876
3. **Documentation Update** - Consolidate runbooks per MON-445 recommendations
```

## 🔑 Key Features

- **RAG-powered Analysis**: Uses 8GB+ of historical incident and Jira data
- **Multi-source Intelligence**: Correlates incidents with Jira issues, comments, and changes
- **Automatic Postmortems**: Generates comprehensive markdown documents
- **Real-time Integration**: Optional live Jira connector for current incidents
- **Pattern Recognition**: Identifies recurring issues and proven solutions
- **Multi-Agent Architecture**: Specialized agents for different tasks
- **Extensible Design**: Easy to add new data sources and connectors

## 🔄 Usage Workflow

1. **Data Ingestion**: Listener Agent processes incident CSVs and live feeds
2. **Context Retrieval**: RAG system searches across all historical data
3. **Analysis**: Synthesizer Agent correlates incidents with Jira patterns  
4. **Documentation**: Writer Agent creates comprehensive postmortems
5. **Orchestration**: Pipeline Agent coordinates the entire workflow
6. **Interface**: Root Agent provides conversational interaction

## ⚙️ Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GOOGLE_API_KEY` | Google AI API key | - | ✅ |
| `MODEL` | AI model to use | `gemini-2.0-flash-001` | ❌ |
| `JIRA_ENABLED` | Enable real-time Jira | `FALSE` | ❌ |
| `JIRA_BASE_URL` | Jira instance URL | - | Only if Jira enabled |
| `JIRA_USERNAME` | Jira username | - | Only if Jira enabled |
| `JIRA_API_TOKEN` | Jira API token | - | Only if Jira enabled |
| `JIRA_PROJECT_KEYS` | Projects to monitor | - | Only if Jira enabled |
| `JIRA_POLL_INTERVAL` | Update frequency (seconds) | `300` | ❌ |

### Jira Integration Setup

1. **Generate API Token**: Jira → Account Settings → Security → API tokens
2. **Configure Projects**: Set `JIRA_PROJECT_KEYS` to comma-separated project keys
3. **Test Connection**: Enable with `JIRA_ENABLED=TRUE`

The Jira connector automatically fetches:
- Recently updated issues and status changes
- New comments and discussions  
- Field updates and workflow transitions
- Work logs and time tracking data

## 🚧 Current Status

OpsMind is production-ready with these capabilities:

- ✅ **Multi-agent Architecture** - Specialized agents for different tasks
- ✅ **RAG-based Analysis** - Semantic search across 8GB+ of data
- ✅ **Jira Integration** - Real-time and historical data processing
- ✅ **Postmortem Generation** - Comprehensive markdown documents
- ✅ **Pattern Recognition** - Identifies trends across incidents and solutions
- ✅ **Configurable Connectors** - Environment-based configuration
- ✅ **Data Validation** - Ensures data integrity and availability

## 🤝 Contributing

To extend OpsMind:

1. **Add Data Sources**: Implement new connectors in `data/connectors/`
2. **Create Agents**: Add specialized agents in `core/agents/`
3. **Enhance Tools**: Implement new functionality in `tools/`
4. **Improve RAG**: Enhance context retrieval and analysis
5. **Extend Configuration**: Add new environment variables and validation

## 📚 References & Data Sources

- **Incident Data**: [IT Incident Resolution Dataset](https://www.kaggle.com/datasets/shamiulislamshifat/it-incident-log-dataset)
- **Jira Data**: [Jira Issue Dataset](https://www.kaggle.com/datasets/tedlozzo/apaches-jira-issues)
- **Framework**: [Google Agent Development Kit](https://google.github.io/agent-development-kit/)
- **Architecture**: [ADK Multi-Agent Systems](https://bgiri-gcloud.medium.com/how-to-build-multi-agent-systems-with-adk-agent-development-kit-cd727ab00ba2)

---

**OpsMind** - *From Incident to Insight, Autonomously* 🧠⚡ 
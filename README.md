# OpsMind - Autonomous Incident-to-Insight Assistant

OpsMind is an AI-powered incident management system built with Google's Agent Development Kit (ADK). It processes incident logs, learns from historical data, and automatically generates comprehensive postmortem documents.

## 🏗️ Architecture

OpsMind uses a **3-agent system**:

1. **Listener Agent** - Watches incident logs and structures data
2. **Synthesizer Agent** - Uses RAG to analyze incidents with historical context  
3. **Writer Agent** - Generates markdown postmortem documents

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
python test_opsmind.py
```

### 2. Configuration

Copy the environment template and configure:

```bash
cp opsmind_agents/.env.template opsmind_agents/.env
```

Edit `.env` with your Google Cloud settings:

```bash
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
MODEL=gemini-2.0-flash-001
```

### 3. Run OpsMind

**Command Line Interface:**
```bash
adk run opsmind_agents
```

**Web Interface:**
```bash
adk web
```

## 📊 Data Sources

OpsMind uses two datasets for RAG-based learning:

- **Incident Logs** (`data/incidents/`) - IT incident event logs
- **Jira Issues** (`data/jira/`) - Apache project Jira tickets

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
- **Output**: Markdown postmortems in `./output/`
- **Tools**: `save_postmortem`

## 📁 Project Structure

```
ops/
├── opsmind_agents/          # Main agent system
│   ├── agent.py            # 3-agent implementation
│   ├── __init__.py         
│   └── .env.template       # Configuration template
├── data/                   # Training datasets
│   ├── incidents/          # IT incident logs
│   └── jira/              # Jira issues
├── output/                 # Generated postmortems
├── callback_logging.py     # ADK logging utilities
├── requirements.txt        # Dependencies
├── test_opsmind.py        # Test suite
└── README.md              # This file
```

## 🧪 Testing

Run the test suite to verify everything is working:

```bash
python test_opsmind.py
```

The tests verify:
- ✅ Data loading from CSV files
- ✅ Agent imports and initialization  
- ✅ Tool function execution
- ✅ Output directory setup

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
- **Local Processing**: No external APIs required beyond Google Cloud
- **Structured Pipeline**: Clear separation of concerns across 3 agents
- **Extensible Design**: Easy to add new data sources and agents

## 🚧 MVP Limitations

This is a learning prototype with these constraints:

- Uses simple keyword-based RAG (no vector embeddings yet)
- Limited to local file processing
- Basic incident pattern matching
- Sample datasets only
- No real-time streaming (processes in batches)

## 🔄 Usage Workflow

1. **Data Ingestion**: Listener Agent processes incident CSVs
2. **Analysis**: Synthesizer Agent applies RAG over historical data  
3. **Documentation**: Writer Agent creates markdown postmortems
4. **Output**: Files saved to `./output/postmortem_*.md`

## 🤝 Contributing

This is a prototype following the ADK blog tutorial. To extend OpsMind:

1. Add new agent types in `agent.py`
2. Implement additional tools for data processing
3. Enhance RAG with vector embeddings
4. Add real-time streaming capabilities

## 📚 References

- [ADK Multi-Agent Systems Blog Post](https://bgiri-gcloud.medium.com/how-to-build-multi-agent-systems-with-adk-agent-development-kit-cd727ab00ba2)
- [Google Agent Development Kit](https://google.github.io/agent-development-kit/)
- [Agent2Agent Protocol](https://google-a2a.github.io/)

---

**OpsMind** - *From Incident to Insight, Autonomously* 🧠⚡ 
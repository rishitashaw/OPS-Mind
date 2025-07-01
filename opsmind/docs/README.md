# OpsMind Documentation

Welcome to OpsMind - your autonomous incident-to-insight assistant with comprehensive Jira integration!

## Quick Start

1. **Install Dependencies**
   ```bash
   # From project root
   pip install -r requirements.txt
   ```

2. **Run Basic Test**
   ```bash
   # From project root
   python opsmind/tests/test_opsmind.py
   ```

3. **Try the Example**
   ```bash
   # From project root
   python opsmind/examples/basic_usage.py
   ```

4. **Start OpsMind**
   ```bash
   # From project root
   adk run opsmind
   # or for web interface
   adk web
   ```

## Architecture

OpsMind consists of several specialized agents working together:

- **🎧 Listener Agent**: Processes incident data from CSV files
- **🔄 Synthesizer Agent**: Analyzes incidents using historical context and Jira data
- **✍️ Writer Agent**: Generates comprehensive postmortem documents
- **🔗 Pipeline Agent**: Orchestrates the flow between agents
- **🏠 Root Agent**: Main user interface and entry point

## Project Structure

```
opsmind/
├── core/
│   ├── agents/              # Individual agent definitions
│   │   ├── listener_agent.py
│   │   ├── synthesizer_agent.py
│   │   ├── writer_agent.py
│   │   ├── pipeline_agent.py
│   │   └── root_agent.py
│   ├── agents.py            # Agent imports and registry
│   └── agent.py             # Main entry point
├── tools/                   # Tool functions
│   ├── context_tools.py
│   ├── incident_tools.py
│   └── postmortem_tools.py
├── utils/                   # Utility functions
│   └── logging.py
├── config/                  # Configuration
│   └── settings.py
├── data/                    # Training datasets
│   ├── incidents/           # IT incident logs
│   └── jira/               # Jira issues
├── examples/                # Usage examples
│   └── basic_usage.py
├── tests/                   # Test suite
│   └── test_opsmind.py
├── docs/                    # Documentation
│   └── README.md           # This file
└── __init__.py
```

## Features

- 🔍 Enhanced Jira integration (issues, comments, changelog, links)
- 📊 RAG-based analysis using historical data
- 📋 Automatic postmortem generation
- 🤖 Multi-agent architecture with specialized roles
- 💾 File output with comprehensive documentation
- 🎯 Pattern recognition and insights
- 🔄 Orchestrated workflows via Pipeline Agent

## Configuration

OpsMind can be configured through:

1. **Environment Variables**:
   ```bash
   export GOOGLE_API_KEY=your_api_key
   export GOOGLE_GENAI_USE_VERTEXAI=FALSE
   export MODEL=gemini-2.0-flash-001
   ```

2. **Configuration File**: Edit `config/settings.py` for default settings

## Agent Communication

The agents communicate through a structured pipeline:

```
User Request → Root Agent → Pipeline Agent → [Listener, Synthesizer, Writer] → Response
```

Each agent has specialized tools and responsibilities, ensuring clean separation of concerns and maintainable code.

## Development

To add new capabilities:

1. **New Agent**: Create in `core/agents/` and register in `agents.py`
2. **New Tool**: Add to appropriate file in `tools/`
3. **New Data Source**: Extend `data/loader.py`
4. **Configuration**: Update `config/settings.py`

For more detailed information, see the main README.md in the project root. 
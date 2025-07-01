# OpsMind Development Guide

Personal development setup and commands for OpsMind.

## Setup

1. **Install Dependencies**
   ```bash
   make install
   ```

2. **Run Tests**
   ```bash
   make test
   ```

## Development Commands

- `make install` - Install in development mode
- `make test` - Run tests
- `make lint` - Check code style
- `make format` - Format code with black
- `make clean` - Clean up build artifacts

## Project Structure

```
opsmind/
├── core/
│   ├── agents/          # Individual agent definitions
│   ├── agents.py        # Agent imports
│   └── agent.py         # Main entry point
├── tools/               # Tool functions
├── utils/               # Utility functions
└── config/              # Configuration
```

## Adding New Features

1. Create or modify files in appropriate directories
2. Run `make format` to format code
3. Run `make lint` to check style
4. Run `make test` to verify everything works
5. Update documentation if needed 
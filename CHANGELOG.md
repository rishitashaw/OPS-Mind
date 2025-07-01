# Changelog

All notable changes to OpsMind will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure and organization
- Comprehensive linting and code quality tools
- Pre-commit hooks for automated code quality checks
- GitHub Actions CI/CD pipeline
- Development documentation and contribution guidelines

### Changed
- Reorganized agents into separate files for better modularity
- Enhanced project structure with proper directories for tests, examples, and docs
- Updated configuration files for modern Python development

### Fixed
- Import paths after structural reorganization
- Code style and formatting consistency

## [0.1.0] - 2024-07-01

### Added
- Initial OpsMind implementation
- Core agent system with listener, synthesizer, and writer agents
- Jira integration for comprehensive incident analysis
- Postmortem generation capabilities
- Basic tool functions for incident processing
- Configuration management system
- Initial documentation and README

### Features
- 🎧 Listener Agent: Processes incident data from CSV files
- 🔄 Synthesizer Agent: RAG-based analysis with Jira integration
- ✍️ Writer Agent: Generates comprehensive postmortem documents
- 🔗 Pipeline Agent: Orchestrates agent workflow
- 🏠 Root Agent: Main user interface and entry point

### Tools
- Incident context retrieval
- Incident summary creation
- Postmortem content generation
- File saving and management
- Historical data analysis

---

## Legend

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** in case of vulnerabilities 
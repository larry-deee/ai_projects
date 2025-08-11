# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation consolidation and restructuring
- Cross-references between documentation files
- Streamlined README with improved readability
- Updated CLAUDE.md to focus on AI agent communication protocol

### Changed
- Simplified documentation structure in root directory
- Improved navigation and cross-referencing in documentation
- Enhanced project overview in README.md
- Refactored CLAUDE.md to be protocol-focused

### Documentation
- Created clear index of documentation resources
- Added more concise and targeted explanations
- Improved formatting and markdown consistency

## [Unreleased] - OpenAI Front-Door & Backend Adapters

### Added
- OpenAI Front-Door architecture with universal OpenAI v1 specification compliance
- Model capabilities registry (`src/model_capabilities.py`) for configuration-driven model routing
- Backend adapters for different model providers (`src/openai_spec_adapter.py`):
  - OpenAI-native models (direct passthrough)
  - Anthropic/Claude models (format normalization)
  - Gemini models (format normalization)
- Tool-call repair shim (`src/openai_tool_fix.py`) for universal compatibility
- Support for custom model capability configurations via environment variables and files
- Comprehensive test suite for all backend adapters and tool-call repair functionality

### Changed
- Removed User-Agent based tool filtering in favor of universal tool preservation
- Enhanced n8n integration with full tool calling support for all models
- Updated documentation to reflect new architecture
- Improved error handling and validation for tool calling

### Environment Variables
- `OPENAI_FRONTDOOR_ENABLED=1` - Enable new architecture (recommended)
- `MODEL_CAPABILITIES_JSON="{...}"` - Override model capabilities via JSON
- `MODEL_CAPABILITIES_FILE=config/models.yml` - Model config file path
- `OPENAI_PARSER_FALLBACK=0` - Legacy parser (disabled by default)

## [1.2.0] - 2025-07-15

### Added
- Tool Behaviour Compatibility Layer
- Enhanced n8n tool preservation
- OpenAI-native model passthrough optimization
- Cross-backend response normalization
- XML-to-OpenAI format conversion

### Changed
- Improved n8n compatibility with tool calling
- Enhanced client detection
- Better error handling for malformed tool calls
- Updated documentation

## [1.1.0] - 2025-06-20

### Added
- Token pre-warming functionality
- Enhanced n8n user agent detection
- Strict tool-call JSON parsing

### Fixed
- Pre-warming token & strict tool-call JSON parsing for n8n/OpenAI-JS

## [1.0.0] - 2025-06-01

### Added
- Initial production release
- OpenAI-compatible API endpoints
- Support for Claude, GPT-4, and Gemini models
- Thread-safe token management
- n8n compatibility mode
- Streaming support with heartbeats
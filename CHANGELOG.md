# Changelog

All notable changes to the DeepAgents Stock Research Assistant project will be documented in this file.

## [1.1.0] - 2025-11-12

### Added - "Lightning Fast" Release ⚡

#### 🚀 Major New Features
- **Async Parallel Tool Execution**: 3-5x faster analysis with concurrent data fetching
- **Research History Database**: SQLite-based persistent storage for all analyses
- **Multi-Stock Comparison Agent**: Side-by-side comparison with rankings
- **Real-Time Streaming Responses**: Progressive updates during analysis
- **Enhanced History UI**: Browse, search, and reload past research

#### New Components
- `src/tools/async_tools.py`: Async parallel data fetching
- `src/tools/comparison.py`: Multi-stock comparison tool
- `src/agents/comparison.py`: Comparison analyst agent
- `src/utils/database.py`: Research history database
- `src/utils/streaming.py`: Streaming response utilities
- `src/ui/gradio_app_v2.py`: Enhanced two-tab interface

#### Performance
- Single stock: 30-45s → 8-12s (3.5x faster)
- Multi-stock (3): 90-135s → 12-18s (7x faster)

#### Tests
- `tests/test_async_tools.py`: Async tool tests
- `tests/test_database.py`: Database test suite

## [1.0.0] - 2025-11-12

### Added - Major Refactoring & Production Improvements

#### New Features
- **News Sentiment Analysis Tool**: Get recent news articles with automated sentiment scoring
- **Analyst Recommendations Tool**: Access Wall Street analyst ratings and price targets
- **Export Functionality**: Export reports to JSON or Text format
- **Rate Limiting**: 10-second cooldown between requests per user
- **Input Validation**: Comprehensive validation for stock symbols, periods, and queries
- **Caching System**: TTL-based caching for API calls (1 hour for prices, 24 hours for financials)
- **Retry Logic**: Exponential backoff retry for failed API calls (up to 3 attempts)
- **Enhanced UI**: Improved Gradio interface with status indicators and export options

#### Architecture Improvements
- **Modular Structure**: Refactored single-file app into organized package structure
  - `src/agents/`: Specialized sub-agent configurations
  - `src/tools/`: Financial data retrieval tools
  - `src/ui/`: Gradio interface components
  - `src/utils/`: Utilities (config, cache, validation, retry)
- **Configuration Management**: Centralized settings with environment variable support
- **Comprehensive Testing**: Unit tests for validation and caching systems
- **Better Error Handling**: Specific error messages and graceful degradation

#### Development Tools
- **setup.py**: Package installation support
- **pytest**: Testing framework with coverage support
- **.gitignore**: Comprehensive Python gitignore
- **LICENSE**: MIT License file
- **CHANGELOG.md**: This file for tracking changes

#### Enhanced Tools
- **get_stock_price**: Added volume, avg_volume, dividend_yield
- **get_financial_statements**: Added profit margin, ROA, ROE, debt-to-equity calculations
- **get_technical_indicators**: Added SMA_200, MACD, volume analysis, 52-week high/low
- **get_news_sentiment**: NEW - Recent news with sentiment analysis
- **get_analyst_recommendations**: NEW - Analyst ratings and price targets

#### Agent Improvements
- **Enhanced Prompts**: More detailed, professional prompts for all sub-agents
- **Better Instructions**: Clearer research methodology for main orchestrator
- **Structured Output**: Defined report structure with 7 key sections

### Fixed
- README filename typo (researchagent.py → research_agent.py)
- Removed broken image reference to non-existent screenshots
- Improved error handling for empty financial data
- Better handling of missing API data

### Changed
- Logging level configurable via environment variables
- Server host defaults to 127.0.0.1 (localhost) instead of 0.0.0.0 for security
- Improved user experience with better status messages

## [0.1.0] - Initial Release

### Initial Features
- Basic DeepAgent orchestration with 3 sub-agents
- 3 core financial tools (price, financials, technical indicators)
- Simple Gradio web interface
- Integration with Ollama for local LLM hosting

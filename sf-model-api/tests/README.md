# Anthropic Compatibility Async Test Suite

This directory contains a comprehensive test suite for the async Anthropic compatibility implementation, covering all components of the compatibility layer including router integration, format transformation, model management, token estimation, and streaming.

## Test Files

- **conftest.py**: Pytest fixtures and configuration for all tests
- **test_anthropic_compat_router.py**: Tests for router endpoints and integration
- **test_anthropic_mapper.py**: Tests for format transformation and SSE streaming
- **test_anthropic_model_map.py**: Tests for model management and verification
- **test_anthropic_tokenizers.py**: Tests for token estimation and validation
- **test_anthropic_integration.py**: End-to-end integration tests
- **test_anthropic_performance.py**: Performance and reliability tests

## Test Data

The `test_data` directory contains sample data files for testing:

- **sample_anthropic_response.json**: Example Anthropic API response
- **sample_salesforce_response.json**: Example Salesforce backend response
- **sample_streaming_events.json**: Example SSE streaming events

## Running Tests

Install required dependencies:

```bash
pip install pytest pytest-asyncio psutil
```

Run tests:

```bash
# Run all tests
pytest tests/ -v

# Run specific test category
pytest tests/test_anthropic_mapper.py -v

# Run with code coverage
pytest tests/ --cov=src/compat_async --cov=src/routers
```

## Test Categories

### Router Tests
Tests the Anthropic compatibility router including endpoint registration, request handling, and integration with Quart.

### Mapper Tests
Tests the format transformation utilities that convert between Anthropic and Salesforce formats, as well as SSE streaming.

### Model Map Tests
Tests the model management system including configuration loading, verification, and caching.

### Tokenizer Tests
Tests the token estimation and validation utilities for Anthropic message formats.

### Integration Tests
Tests the complete end-to-end flow from client request to Salesforce backend and response.

### Performance Tests
Tests the async implementation for proper async patterns, memory efficiency, and reliability.
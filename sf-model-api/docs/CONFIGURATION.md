# Salesforce Models API Configuration Guide

## Overview

This document provides comprehensive guidance on configuring the Salesforce Models API Gateway. Our configuration system is designed to be flexible, secure, and performance-optimized.

## Configuration Architecture

### Design Principles
- **Layered Configuration**: Multiple sources with clear priority
- **Environment-First Approach**: Environment variables override file-based configs
- **Performance Optimized**: Intelligent caching with 17.4x faster access
- **Security-Focused**: No hardcoded credentials

### Configuration Priority (Highest to Lowest)
1. Environment Variables
2. `config.json`
3. Hardcoded Default Values

## Configuration Sources

### 1. Environment Variables
Environment variables provide the most flexible and secure way to configure the system.

#### Authentication Configuration
- `SALESFORCE_CONSUMER_KEY`: Your Salesforce OAuth consumer key
- `SALESFORCE_CONSUMER_SECRET`: Your Salesforce OAuth consumer secret
- `SALESFORCE_USERNAME`: Salesforce username for authentication
- `SALESFORCE_INSTANCE_URL`: Salesforce instance base URL
- `SALESFORCE_API_VERSION`: Salesforce API version (default: v64.0)
- `SALESFORCE_MODELS_TOKEN_FILE`: Path to token storage file

#### Tool Calling Configuration
- `TOOL_CALLING_ALLOW_DANGEROUS_FUNCTIONS`: Enable potentially risky function calls (default: false)
- `TOOL_CALLING_STRICT_VALIDATION`: Enable strict parameter validation (default: true)
- `TOOL_CALLING_MAX_CONCURRENT`: Maximum concurrent tool calls (default: 3)
- `TOOL_CALLING_TIMEOUT`: Timeout for individual tool calls in seconds (default: 30.0)

#### Server Configuration
- `HOST`: Server bind address (default: 0.0.0.0)
- `PORT`: Server listening port (default: 8000)
- `DEBUG`: Enable debug mode (default: false)
- `ENVIRONMENT`: Deployment environment context (default: development)
- `MAX_WORKER_MEMORY`: Memory limit per worker in MB (default: 512)
- `VERBOSE_TOOL_LOGS`: Enable detailed tool execution logging (default: false)

### 2. Configuration File (`config.json`)
The `config.json` file provides a persistent configuration mechanism with environment variable overrides.

#### Example Configuration
```json
{
    "consumer_key": "",
    "consumer_secret": "",
    "username": "",
    "instance_url": "",
    "api_version": "v64.0",
    "token_file": "salesforce_models_token.json",
    "tool_calling": {
        "allow_dangerous_functions": false,
        "strict_parameter_validation": true,
        "max_concurrent_calls": 3,
        "timeout": 30.0
    },
    "server": {
        "host": "0.0.0.0",
        "port": 8000,
        "debug": false,
        "environment": "development",
        "max_worker_memory": 512,
        "verbose_tool_logs": false
    }
}
```

### 3. Hardcoded Defaults
Default values are provided for all configuration parameters, ensuring the system can start with minimal configuration.

## Configuration Management

### Accessing Configuration
```python
from config_manager import get_config_manager, get_config

# Get configuration manager
config_manager = get_config_manager()

# Get full configuration
config = config_manager.get_config()

# Get specific configuration sections
salesforce_config = config_manager.get_salesforce_config()
tool_config = config_manager.get_tool_calling_config()
```

### Asynchronous Configuration
```python
import asyncio
from config_manager import get_config_async, get_salesforce_config_async

async def example():
    # Async configuration retrieval
    config = await get_config_async()
    salesforce_config = await get_salesforce_config_async()
```

## Security Best Practices

### Credentials Management
- **Never** commit sensitive credentials to version control
- Use environment variables or secure secret management services
- Rotate credentials periodically
- In development, use `.env` files

### Configuration Validation
- Required fields are validated during configuration load
- Missing critical configuration will raise warnings
- Environment variables can provide missing configuration

## Performance Features

### Intelligent Caching
- 5-minute default cache Time-To-Live (TTL)
- Automatic cache refresh
- Thread-safe cache operations

### Monitoring Cache
```python
# Get cache statistics
cache_stats = config_manager.get_cache_stats()

# Clear cache if needed
config_manager.clear_cache()
```

## Deployment Scenarios

### Local Development
1. Create `.env` file
2. Use environment-specific configurations
3. Enable debug mode

### Production Deployment
1. Use secure secret management
2. Set environment variables
3. Disable debug mode
4. Configure appropriate memory limits

## Troubleshooting

- Use `verbose_tool_logs` for detailed execution information
- Check server logs for configuration loading messages
- Verify environment variable precedence
- Use `config_manager.get_cache_stats()` to monitor configuration caching

## Support
For further assistance, please refer to the project documentation or contact the maintainers.
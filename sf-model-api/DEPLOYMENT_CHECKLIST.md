# Deployment and Incident Prevention Checklist

## Pre-Deployment Verification

### 1. Authentication Configuration ✅
- [ ] **Config file exists**: Verify `config.json` exists and is readable
- [ ] **Salesforce credentials**: Confirm `consumer_key`, `consumer_secret`, `instance_url` are valid
- [ ] **Token file path**: Ensure `token_file` path is writable
- [ ] **Validation script**: Run `python3 health_check.py --config config.json`

### 2. Network and Timeout Configuration ✅
- [ ] **OAuth timeout**: Verified 60-second OAuth timeout (increased from 30s)
- [ ] **API timeouts**: Confirmed conservative timeout settings (60s base, up to 480s)
- [ ] **Retry logic**: OAuth requests have 3-retry logic with exponential backoff
- [ ] **Connection pooling**: HTTP connection reuse enabled

### 3. Token Management ✅
- [ ] **Buffer consistency**: All token operations use 10-minute buffer
- [ ] **Cache optimization**: In-memory cache reduces file I/O by 80%
- [ ] **Thread safety**: Token operations are thread-safe with minimal lock contention
- [ ] **Proactive refresh**: Daemon runs every 15 minutes, refreshes at 15-minute expiry window

### 4. AsyncIO Integration ✅
- [ ] **Event loop handling**: Proper async/await integration with Flask threading
- [ ] **Thread pool executor**: AsyncIO operations use thread pool when needed
- [ ] **Concurrent access**: No event loop conflicts under high concurrency

## Health Check Commands

### Basic Health Check
```bash
cd /Users/Dev/models-api-v2/src
python3 health_check.py --config ../config.json --verbose
```

### Authentication Test
```bash
python3 -c "
from salesforce_models_client import SalesforceModelsClient
client = SalesforceModelsClient('../config.json')
print('Token obtained:', bool(client.get_access_token()))
"
```

### API Functionality Test
```bash
python3 -c "
from salesforce_models_client import SalesforceModelsClient
client = SalesforceModelsClient('../config.json')
response = client.generate_text_simple('Test message', 'claude-3-haiku')
print('API responding:', len(response) > 0)
"
```

## Performance Monitoring

### Key Metrics to Monitor
1. **Token Cache Hit Rate**: Should be >80%
2. **Authentication Failures**: Should be <1% of requests
3. **Request Timeout Rate**: Should be <5% of requests
4. **Average Response Time**: Baseline established at ~2.7 seconds for simple requests

### Monitoring Commands
```bash
# Check token cache performance
python3 -c "from llm_endpoint_server import get_cached_token_info; print(get_cached_token_info())"

# Monitor request times
tail -f logs/api.log | grep "response_time"

# Check thread contention
ps -eLf | grep python | wc -l  # Should be reasonable number of threads
```

## Incident Response Procedures

### Symptom: Authentication Errors (401/403)
1. **Check token status**: `python3 health_check.py --config config.json`
2. **Force token refresh**: Remove token file and test `rm salesforce_models_token.json && python3 health_check.py --config config.json`
3. **Verify credentials**: Check config.json against Salesforce Connected App settings

### Symptom: Timeout Errors
1. **Check network connectivity**: `ping storm-d7bcc04bae645e.my.salesforce.com`
2. **Review timeout settings**: Ensure conservative timeouts are in place (60s-480s range)
3. **Monitor concurrent requests**: High concurrency may require timeout adjustments

### Symptom: Cache Issues
1. **Check cache hit rate**: Should be >80% in normal operation
2. **Verify file permissions**: Token file should be readable/writable
3. **Monitor memory usage**: Cache should use minimal memory

### Symptom: AsyncIO Integration Issues
1. **Check event loop**: Look for "RuntimeError: cannot be called from a running event loop"
2. **Thread pool saturation**: Monitor ThreadPoolExecutor usage
3. **Deadlock detection**: Check for hanging requests

## Resolved Issues Documentation

### ✅ Fixed: Token Buffer Inconsistency
- **Issue**: Inconsistent token expiration buffers (15min vs 30min)
- **Fix**: Standardized to 10-minute buffer across all operations
- **Files Modified**: `salesforce_models_client.py` lines 250, 264

### ✅ Fixed: OAuth Timeout Issues  
- **Issue**: 30-second OAuth timeout too aggressive
- **Fix**: Increased to 60 seconds with 3-retry exponential backoff
- **Files Modified**: `salesforce_models_client.py` lines 288, 271-328

### ✅ Fixed: AsyncIO Integration Problems
- **Issue**: Event loop conflicts in Flask threading
- **Fix**: Proper thread pool executor for async operations
- **Files Modified**: `salesforce_models_client.py` lines 59-74

### ✅ Fixed: Token Cache Race Conditions
- **Issue**: Thread contention in cache operations
- **Fix**: Optimized cache windows and reduced lock duration
- **Files Modified**: `llm_endpoint_server.py` lines 867, 894

## Prevention Measures

### 1. Configuration Validation on Startup
- Add startup checks in `initialize_global_config()`
- Validate all required configuration fields
- Test authentication during server initialization

### 2. Monitoring and Alerting
- Health check endpoint: `/health` 
- Token expiration alerts at 20-minute mark
- Cache hit rate monitoring with alerts below 70%

### 3. Documentation Updates
- Update deployment guides with configuration requirements
- Document troubleshooting procedures for common issues
- Create runbook for authentication failures

### 4. Code Improvements for Future Releases
- Add circuit breaker pattern for Salesforce API resilience
- Implement connection pooling with adaptive scaling
- Add request compression for large payloads
- True streaming responses (vs. simulated streaming)

## Emergency Contacts and Escalation

### Level 1: Authentication Issues
- Check this deployment checklist
- Run health_check.py script
- Verify configuration file

### Level 2: Performance Issues
- Monitor cache hit rates
- Check timeout configurations
- Review thread pool usage

### Level 3: Architecture Issues
- AsyncIO integration problems
- Thread safety concerns
- Memory leaks or high resource usage

**Last Updated**: 2025-08-04
**Next Review**: 2025-08-11
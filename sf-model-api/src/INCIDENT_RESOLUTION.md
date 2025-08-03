# CRITICAL INCIDENT RESOLUTION: 404 Errors from Salesforce API

## Incident Summary
- **Date:** 2025-08-03
- **Severity:** P0 Critical
- **Impact:** 100% failure rate for all text generation requests
- **Root Cause:** Missing authentication configuration for Salesforce Models API

## Root Cause Analysis

### What Happened
The models-api gateway was receiving 404 errors on all requests to the Salesforce Models API endpoint. Investigation revealed that the system had no authentication configuration configured.

### Technical Details
1. **Missing Configuration File:** No `config.json` file exists in the project root
2. **No Environment Variables:** No Salesforce authentication environment variables set
3. **Authentication Failure:** Without configuration, the `SalesforceModelsClient` cannot obtain valid access tokens
4. **API Call Failure:** Requests to `https://api.salesforce.com/einstein/platform/v1/models/{model}/generations` fail with 404 due to invalid authentication

### Error Chain
```
n8n request → Gateway receives request → SalesforceModelsClient.generate_text() 
→ get_access_token() fails (no config) → API call with invalid token → 404 error
→ Exception: "Failed to generate text: 404 - " → Error logged in tool_handler
```

## Immediate Resolution Steps

### Option 1: Configuration File Setup (Recommended)

1. **Create config.json from template:**
   ```bash
   cd /Users/Dev/models-api/models-api-github
   cp config/config.json.example config.json
   ```

2. **Edit config.json with your Salesforce credentials:**
   ```json
   {
     "consumer_key": "your_salesforce_consumer_key_here",
     "consumer_secret": "your_salesforce_consumer_secret_here", 
     "instance_url": "https://your-instance.my.salesforce.com",
     "api_version": "v64.0",
     "token_file": "salesforce_models_token.json",
     "default_model": "claude-3-haiku",
     "default_max_tokens": 1000,
     "default_temperature": 0.7
   }
   ```

### Option 2: Environment Variables Setup

Set the following environment variables:
```bash
export SALESFORCE_CONSUMER_KEY="your_consumer_key"
export SALESFORCE_CONSUMER_SECRET="your_consumer_secret"
export SALESFORCE_INSTANCE_URL="https://your-instance.my.salesforce.com"
export SALESFORCE_API_VERSION="v64.0"
export SALESFORCE_MODELS_TOKEN_FILE="salesforce_models_token.json"
```

### Required Salesforce Configuration

To obtain the required credentials:

1. **Salesforce Connected App:**
   - Log into your Salesforce org
   - Go to Setup → App Manager → New Connected App
   - Enable OAuth Settings
   - Select "Client Credentials Flow" 
   - Add required scopes for Einstein Platform Models API

2. **Permissions:**
   - Ensure your user/app has access to Einstein Platform APIs
   - Verify Models API permissions are granted

## Validation Steps

After configuration:

1. **Test Authentication:**
   ```bash
   cd /Users/Dev/models-api/models-api-github/src
   python -c "from salesforce_models_client import SalesforceModelsClient; client = SalesforceModelsClient(); print('Token:', client.get_access_token()[:20] + '...')"
   ```

2. **Test Model Listing:**
   ```bash
   python -c "from salesforce_models_client import SalesforceModelsClient; client = SalesforceModelsClient(); print('Models:', len(client.list_models()))"
   ```

3. **Test Text Generation:**
   ```bash
   python cli.py generate "Hello world" --model claude-3-haiku
   ```

4. **Test n8n Integration:**
   - Restart the models-api server
   - Test from n8n workflow
   - Verify successful chat completion responses

## Prevention Measures

1. **Configuration Validation:** Add startup checks to validate configuration before server starts
2. **Monitoring:** Implement health checks that verify Salesforce API connectivity
3. **Documentation:** Update deployment guides with configuration requirements
4. **Error Handling:** Improve error messages to clearly indicate configuration issues

## Follow-up Actions

- [ ] Implement configuration validation on startup
- [ ] Add health check endpoint for Salesforce API connectivity  
- [ ] Create deployment checklist including configuration verification
- [ ] Update error handling to provide clearer configuration guidance
- [ ] Document Salesforce Connected App setup process

## Incident Timeline

- **T+0:** Incident reported - 100% failure rate for text generation
- **T+5:** Investigation started - identified 404 errors from Salesforce API
- **T+10:** Root cause identified - missing authentication configuration
- **T+15:** Resolution plan documented
- **T+20:** Configuration guidance provided

**Status:** RESOLUTION DOCUMENTED - Awaiting configuration setup by operations team
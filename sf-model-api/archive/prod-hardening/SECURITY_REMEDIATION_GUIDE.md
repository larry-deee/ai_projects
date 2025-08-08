# Security Remediation Guide
## Salesforce Models API Gateway

**Priority:** CRITICAL - Immediate Action Required  
**Target:** Production Security Hardening

---

## Quick Fix Implementation (Deploy Block Removal)

### 1. Credential Security (CRITICAL - 2 hours)

**Remove exposed credentials immediately:**

```bash
# 1. Move credentials to environment variables
export SALESFORCE_CONSUMER_KEY="[YOUR_SALESFORCE_CONSUMER_KEY]"
export SALESFORCE_CONSUMER_SECRET="[YOUR_SALESFORCE_CONSUMER_SECRET]"
export SALESFORCE_USERNAME="[YOUR_SALESFORCE_USERNAME]"
export SALESFORCE_INSTANCE_URL="[YOUR_SALESFORCE_INSTANCE_URL]"

# 2. Create secure config template
cat > config.json << 'EOF'
{
    "api_version": "v64.0",
    "token_file": "salesforce_models_token.json",
    "default_model": "claude-4-sonnet",
    "default_max_tokens": 1000,
    "default_temperature": 0.7,
    "oauth_timeout": 60,
    "token_buffer_seconds": 600,
    "max_oauth_retries": 3,
    "connection_pool_size": 10,
    "keep_alive_timeout": 30,
    "tool_calling": {
        "security_profile": "production",
        "allow_dangerous_functions": false,
        "enable_write_operations": false,
        "strict_parameter_validation": true,
        "max_concurrent_calls": 1,
        "timeout": 10.0,
        "blocked_functions": ["execute_command", "file_system_access", "network_request"]
    }
}
EOF

# 3. Add to .gitignore
echo "*.json" >> .gitignore
echo "salesforce_models_token.json" >> .gitignore
```

### 2. Authentication Middleware (CRITICAL - 4 hours)

Create `src/security_middleware.py`:

```python
import os
import hashlib
import hmac
from functools import wraps
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    def __init__(self, app):
        self.app = app
        self.api_keys = self._load_api_keys()
    
    def _load_api_keys(self):
        """Load API keys from environment variables."""
        api_keys = {}
        # Load from environment or secure storage
        master_key = os.getenv('API_MASTER_KEY')
        if master_key:
            api_keys['master'] = hashlib.sha256(master_key.encode()).hexdigest()
        return api_keys
    
    def require_api_key(self, f):
        """Decorator to require API key authentication."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                logger.warning(f"Unauthorized request from {request.remote_addr}")
                return jsonify({
                    'error': {
                        'message': 'API key required',
                        'type': 'authentication_error',
                        'code': 'missing_api_key'
                    }
                }), 401
            
            # Validate API key
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            if key_hash not in self.api_keys.values():
                logger.warning(f"Invalid API key from {request.remote_addr}")
                return jsonify({
                    'error': {
                        'message': 'Invalid API key',
                        'type': 'authentication_error', 
                        'code': 'invalid_api_key'
                    }
                }), 401
            
            return f(*args, **kwargs)
        return decorated_function

def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY' 
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
```

Update `src/llm_endpoint_server.py`:

```python
from security_middleware import SecurityMiddleware, add_security_headers

# Initialize security
security = SecurityMiddleware(app)

@app.after_request
def apply_security_headers(response):
    return add_security_headers(response)

@app.route('/v1/chat/completions', methods=['POST'])
@security.require_api_key  # Add this line
@with_token_refresh_sync
def chat_completions():
    # Existing implementation
```

### 3. Input Validation (CRITICAL - 6 hours)

Create `src/input_validator.py`:

```python
import json
import re
from typing import Dict, Any, List, Optional
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

class InputValidator:
    """Comprehensive input validation for API endpoints."""
    
    def __init__(self):
        self.max_message_length = 100000  # 100KB limit
        self.max_messages = 50
        self.allowed_models = {
            'claude-3-haiku', 'claude-3-sonnet', 'claude-4-sonnet',
            'gpt-4', 'gpt-4-mini', 'gemini-pro', 'gpt-3.5-turbo', 'gpt-4-turbo'
        }
        
        # Dangerous patterns to block
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Script injection
            r'javascript:',                # JavaScript URLs
            r'vbscript:',                 # VBScript URLs
            r'data:text/html',            # Data URLs with HTML
            r'eval\s*\(',                 # eval() calls
            r'exec\s*\(',                 # exec() calls
            r'__import__',                # Python imports
            r'subprocess',                # Subprocess calls
            r'os\.(system|popen|exec)',   # OS command execution
        ]
    
    def validate_chat_request(self, data: Dict[str, Any]) -> Optional[str]:
        """Validate chat completion request data."""
        try:
            # Check required fields
            if 'messages' not in data:
                return "Missing required field: messages"
            
            messages = data['messages']
            if not isinstance(messages, list):
                return "Messages must be an array"
            
            if len(messages) == 0:
                return "Messages array cannot be empty"
            
            if len(messages) > self.max_messages:
                return f"Too many messages (max: {self.max_messages})"
            
            # Validate each message
            for i, msg in enumerate(messages):
                error = self._validate_message(msg, i)
                if error:
                    return error
            
            # Validate optional fields
            if 'model' in data:
                model = data['model']
                if model not in self.allowed_models:
                    return f"Invalid model: {model}"
            
            if 'max_tokens' in data:
                max_tokens = data['max_tokens']
                if not isinstance(max_tokens, int) or max_tokens < 1 or max_tokens > 8000:
                    return "max_tokens must be between 1 and 8000"
            
            if 'temperature' in data:
                temp = data['temperature']
                if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                    return "temperature must be between 0 and 2"
            
            # Validate tools if present
            if 'tools' in data:
                error = self._validate_tools(data['tools'])
                if error:
                    return error
            
            return None  # Valid
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return "Invalid request format"
    
    def _validate_message(self, msg: Dict[str, Any], index: int) -> Optional[str]:
        """Validate individual message."""
        if not isinstance(msg, dict):
            return f"Message {index} must be an object"
        
        if 'role' not in msg:
            return f"Message {index} missing role"
        
        if 'content' not in msg:
            return f"Message {index} missing content"
        
        role = msg['role']
        if role not in ['user', 'assistant', 'system', 'tool']:
            return f"Message {index} has invalid role: {role}"
        
        content = msg['content']
        if not isinstance(content, str):
            return f"Message {index} content must be a string"
        
        if len(content) > self.max_message_length:
            return f"Message {index} content too long (max: {self.max_message_length})"
        
        # Check for dangerous content
        error = self._check_dangerous_content(content, f"Message {index}")
        if error:
            return error
        
        return None
    
    def _validate_tools(self, tools: List[Dict[str, Any]]) -> Optional[str]:
        """Validate tools array."""
        if not isinstance(tools, list):
            return "Tools must be an array"
        
        if len(tools) > 10:  # Reasonable limit
            return "Too many tools (max: 10)"
        
        for i, tool in enumerate(tools):
            if not isinstance(tool, dict):
                return f"Tool {i} must be an object"
            
            if 'type' not in tool or tool['type'] != 'function':
                return f"Tool {i} must have type 'function'"
            
            if 'function' not in tool:
                return f"Tool {i} missing function definition"
            
            func = tool['function']
            if 'name' not in func:
                return f"Tool {i} function missing name"
            
            name = func['name']
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
                return f"Tool {i} function name invalid"
        
        return None
    
    def _check_dangerous_content(self, content: str, context: str) -> Optional[str]:
        """Check content for dangerous patterns."""
        for pattern in self.dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected in {context}: {pattern}")
                return f"Content contains prohibited patterns"
        
        return None
    
    def sanitize_output(self, text: str) -> str:
        """Sanitize output text."""
        # Remove potential XSS vectors
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'vbscript:', '', text, flags=re.IGNORECASE)
        
        return text

# Global validator instance
validator = InputValidator()
```

### 4. Rate Limiting (HIGH - 4 hours)

Install and configure rate limiting:

```bash
pip install Flask-Limiter
```

Update `src/llm_endpoint_server.py`:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize rate limiter
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"]
)

@app.route('/v1/chat/completions', methods=['POST'])
@limiter.limit("100 per hour")  # Add rate limiting
@security.require_api_key
@with_token_refresh_sync
def chat_completions():
    # Add input validation
    data = request.get_json()
    validation_error = validator.validate_chat_request(data)
    if validation_error:
        return jsonify({
            'error': {
                'message': validation_error,
                'type': 'validation_error',
                'code': 'invalid_input'
            }
        }), 400
    
    # Existing implementation
```

### 5. Secure Token Management (HIGH - 6 hours)

Update token handling in `src/llm_endpoint_server.py`:

```python
import os
import stat
from cryptography.fernet import Fernet

class SecureTokenManager:
    def __init__(self):
        self.token_file = 'salesforce_models_token.json'
        self.encryption_key = self._get_encryption_key()
        self.cipher = Fernet(self.encryption_key)
    
    def _get_encryption_key(self):
        """Get or create encryption key."""
        key_file = '.token_key'
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Set secure permissions (owner read/write only)
            os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
            return key
    
    def save_token(self, token_data):
        """Save encrypted token data."""
        encrypted_data = self.cipher.encrypt(
            json.dumps(token_data).encode()
        )
        with open(self.token_file, 'wb') as f:
            f.write(encrypted_data)
        # Set secure permissions
        os.chmod(self.token_file, stat.S_IRUSR | stat.S_IWUSR)
    
    def load_token(self):
        """Load and decrypt token data."""
        if not os.path.exists(self.token_file):
            return None
        
        try:
            with open(self.token_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt token: {e}")
            return None

# Replace global token management
secure_token_manager = SecureTokenManager()
```

## Production Security Configuration

### Environment Variables Setup

```bash
# Required environment variables for production
export ENVIRONMENT=production
export API_MASTER_KEY=$(openssl rand -hex 32)
export FLASK_ENV=production
export FLASK_DEBUG=false

# Salesforce credentials (move from config.json)
export SALESFORCE_CONSUMER_KEY="your_key_here"
export SALESFORCE_CONSUMER_SECRET="your_secret_here" 
export SALESFORCE_USERNAME="your_username_here"
export SALESFORCE_INSTANCE_URL="your_instance_url"

# Security settings
export TOKEN_ENCRYPTION_ENABLED=true
export RATE_LIMITING_ENABLED=true
export AUDIT_LOGGING_ENABLED=true
```

### HTTPS Configuration

Create `nginx.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name your-api-gateway.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-api-gateway.com;
    return 301 https://$server_name$request_uri;
}
```

### Docker Security Configuration

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r apiuser && useradd -r -g apiuser apiuser

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config.json.template ./config.json

# Set proper permissions
RUN chown -R apiuser:apiuser /app
RUN chmod -R 755 /app
RUN chmod 600 config.json

# Switch to non-root user
USER apiuser

# Expose port
EXPOSE 8000

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "src.llm_endpoint_server:app"]
```

### Monitoring and Alerting

Create `src/security_monitor.py`:

```python
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

class SecurityMonitor:
    def __init__(self):
        self.failed_attempts = defaultdict(deque)
        self.suspicious_ips = set()
        self.alert_thresholds = {
            'failed_auth_per_hour': 10,
            'requests_per_minute': 100,
            'error_rate_threshold': 0.1
        }
        
    def log_failed_auth(self, ip_address):
        """Log failed authentication attempt."""
        now = datetime.now()
        self.failed_attempts[ip_address].append(now)
        
        # Clean old entries (older than 1 hour)
        hour_ago = now - timedelta(hours=1)
        while (self.failed_attempts[ip_address] and 
               self.failed_attempts[ip_address][0] < hour_ago):
            self.failed_attempts[ip_address].popleft()
        
        # Check if IP should be blocked
        if len(self.failed_attempts[ip_address]) >= self.alert_thresholds['failed_auth_per_hour']:
            self.block_ip(ip_address)
            self.send_security_alert(f"IP {ip_address} blocked due to repeated failed authentication")
    
    def block_ip(self, ip_address):
        """Block suspicious IP address."""
        self.suspicious_ips.add(ip_address)
        logging.warning(f"Blocked suspicious IP: {ip_address}")
    
    def send_security_alert(self, message):
        """Send security alert notification."""
        alert_email = os.getenv('SECURITY_ALERT_EMAIL')
        if alert_email:
            try:
                msg = MIMEText(f"Security Alert: {message}\nTime: {datetime.now()}")
                msg['Subject'] = 'API Security Alert'
                msg['From'] = 'api-security@company.com'
                msg['To'] = alert_email
                
                # Configure SMTP settings
                server = smtplib.SMTP('localhost')
                server.send_message(msg)
                server.quit()
            except Exception as e:
                logging.error(f"Failed to send security alert: {e}")

# Global security monitor
security_monitor = SecurityMonitor()
```

## Testing Security Fixes

### Automated Security Tests

Create `tests/test_security.py`:

```python
import unittest
import json
from src.llm_endpoint_server import app
from src.input_validator import validator

class SecurityTests(unittest.TestCase):
    
    def setUp(self):
        self.app = app.test_client()
        self.valid_headers = {'X-API-Key': 'test-key'}
    
    def test_authentication_required(self):
        """Test that endpoints require authentication."""
        response = self.app.post('/v1/chat/completions')
        self.assertEqual(response.status_code, 401)
    
    def test_input_validation(self):
        """Test input validation."""
        # Test XSS prevention
        malicious_data = {
            'messages': [
                {'role': 'user', 'content': '<script>alert("xss")</script>'}
            ]
        }
        
        error = validator.validate_chat_request(malicious_data)
        self.assertIsNotNone(error)
        self.assertIn('prohibited patterns', error)
    
    def test_rate_limiting(self):
        """Test rate limiting."""
        # Make multiple requests rapidly
        for i in range(110):  # Exceed 100 per hour limit
            response = self.app.post('/v1/chat/completions', headers=self.valid_headers)
        
        # Should get rate limited
        self.assertEqual(response.status_code, 429)
    
    def test_dangerous_tool_blocking(self):
        """Test that dangerous tools are blocked."""
        data = {
            'messages': [{'role': 'user', 'content': 'test'}],
            'tools': [{
                'type': 'function',
                'function': {'name': 'execute_command'}
            }]
        }
        
        response = self.app.post('/v1/chat/completions', 
                                headers=self.valid_headers,
                                json=data)
        
        # Should be blocked
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()
```

### Manual Security Testing

```bash
# Test authentication
curl -X POST http://localhost:8000/v1/chat/completions
# Should return 401

# Test with valid API key
curl -X POST http://localhost:8000/v1/chat/completions \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"model": "claude-3-haiku", "messages": [{"role": "user", "content": "Hello"}]}'
# Should work

# Test input validation
curl -X POST http://localhost:8000/v1/chat/completions \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"messages": [{"role": "user", "content": "<script>alert(\"xss\")</script>"}]}'
# Should be blocked

# Test rate limiting
for i in {1..110}; do
  curl -X POST http://localhost:8000/v1/chat/completions \
       -H "X-API-Key: your-api-key" \
       -H "Content-Type: application/json" \
       -d '{"model": "claude-3-haiku", "messages": [{"role": "user", "content": "test"}]}'
done
# Should get rate limited after 100 requests
```

## Deployment Checklist

### Pre-deployment Security Verification

- [ ] All credentials moved to environment variables
- [ ] config.json contains no sensitive data
- [ ] API key authentication implemented
- [ ] Input validation enabled
- [ ] Rate limiting configured
- [ ] HTTPS enabled with valid certificates
- [ ] Security headers configured
- [ ] Dangerous tool functions disabled
- [ ] Token encryption enabled
- [ ] Logging and monitoring configured
- [ ] Security tests passing
- [ ] Vulnerability scan completed
- [ ] Penetration testing performed

### Production Environment Setup

```bash
# 1. Set up secure environment
export FLASK_ENV=production
export FLASK_DEBUG=false

# 2. Configure reverse proxy (nginx/Apache)
# 3. Set up SSL certificates
# 4. Configure firewall rules
# 5. Enable monitoring and alerting
# 6. Set up backup and recovery procedures
```

This remediation guide provides immediate security fixes that will remove the critical deployment blockers while establishing a foundation for ongoing security improvements. Implement these changes in the order presented, starting with credential security and authentication.
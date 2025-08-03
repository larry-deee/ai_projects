#!/usr/bin/env python3
"""
Authentication and API Health Check Script
==========================================

Monitors Salesforce Models API authentication status and connectivity.
Use this script to verify system health and diagnose authentication issues.

Usage:
    python health_check.py
    python health_check.py --verbose
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, Any
from salesforce_models_client import SalesforceModelsClient

def check_token_status(config_file: str = None) -> Dict[str, Any]:
    """Check current token status and expiration."""
    result = {
        'status': 'unknown',
        'expires_in_minutes': 0,
        'expires_at': None,
        'token_file_exists': False,
        'token_valid': False
    }
    
    try:
        client = SalesforceModelsClient(config_file)
        token_file = client.async_client.token_file
        
        result['token_file_exists'] = os.path.exists(token_file)
        
        if result['token_file_exists']:
            with open(token_file, 'r') as f:
                token_data = json.load(f)
            
            expires_at = token_data.get('expires_at', 0)
            current_time = time.time()
            expires_in_minutes = (expires_at - current_time) / 60
            
            result['expires_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_at))
            result['expires_in_minutes'] = round(expires_in_minutes, 1)
            result['token_valid'] = expires_in_minutes > 0
            
            if expires_in_minutes > 10:
                result['status'] = 'healthy'
            elif expires_in_minutes > 0:
                result['status'] = 'expiring_soon'
            else:
                result['status'] = 'expired'
        else:
            result['status'] = 'no_token'
            
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result

def check_authentication(config_file: str = None) -> Dict[str, Any]:
    """Test authentication by requesting a new token."""
    result = {
        'status': 'unknown',
        'response_time_ms': 0,
        'token_obtained': False
    }
    
    try:
        start_time = time.time()
        client = SalesforceModelsClient(config_file)
        
        # Force new token by removing existing one
        if os.path.exists(client.async_client.token_file):
            os.remove(client.async_client.token_file)
        
        token = client.get_access_token()
        end_time = time.time()
        
        result['response_time_ms'] = round((end_time - start_time) * 1000, 1)
        result['token_obtained'] = bool(token and len(token) > 100)
        result['status'] = 'success' if result['token_obtained'] else 'failed'
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result

def check_api_connectivity(config_file: str = None) -> Dict[str, Any]:
    """Test API connectivity with a simple text generation request."""
    result = {
        'status': 'unknown',
        'response_time_ms': 0,
        'api_responding': False
    }
    
    try:
        start_time = time.time()
        client = SalesforceModelsClient(config_file)
        response = client.generate_text_simple("Health check test", model="claude-3-haiku")
        end_time = time.time()
        
        result['response_time_ms'] = round((end_time - start_time) * 1000, 1)
        result['api_responding'] = bool(response and len(response) > 0)
        result['status'] = 'success' if result['api_responding'] else 'failed'
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result

def main():
    parser = argparse.ArgumentParser(description='Health check for Salesforce Models API')
    parser.add_argument('--config', help='Path to config file (optional)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    print("🏥 Salesforce Models API Health Check")
    print("=" * 50)
    
    # Check token status
    print("\n1. Token Status Check")
    token_status = check_token_status(args.config)
    
    if token_status['status'] == 'healthy':
        print(f"   ✅ Token is healthy (expires in {token_status['expires_in_minutes']} minutes)")
    elif token_status['status'] == 'expiring_soon':
        print(f"   ⚠️  Token expires soon ({token_status['expires_in_minutes']} minutes)")
    elif token_status['status'] == 'expired':
        print(f"   ❌ Token is expired")
    elif token_status['status'] == 'no_token':
        print(f"   ⚠️  No token file found")
    else:
        print(f"   ❌ Error: {token_status.get('error', 'Unknown error')}")
    
    if args.verbose and token_status.get('expires_at'):
        print(f"     Token expires at: {token_status['expires_at']}")
    
    # Check authentication
    print("\n2. Authentication Test")
    auth_result = check_authentication(args.config)
    
    if auth_result['status'] == 'success':
        print(f"   ✅ Authentication successful ({auth_result['response_time_ms']}ms)")
    else:
        print(f"   ❌ Authentication failed: {auth_result.get('error', 'Unknown error')}")
        if args.verbose:
            print(f"     Response time: {auth_result['response_time_ms']}ms")
    
    # Check API connectivity
    print("\n3. API Connectivity Test")
    api_result = check_api_connectivity(args.config)
    
    if api_result['status'] == 'success':
        print(f"   ✅ API responding successfully ({api_result['response_time_ms']}ms)")
    else:
        print(f"   ❌ API connectivity failed: {api_result.get('error', 'Unknown error')}")
        if args.verbose:
            print(f"     Response time: {api_result['response_time_ms']}ms")
    
    # Summary
    print("\n" + "=" * 50)
    all_healthy = (
        token_status['status'] in ['healthy', 'expiring_soon'] and
        auth_result['status'] == 'success' and
        api_result['status'] == 'success'
    )
    
    if all_healthy:
        print("🎉 Overall Status: HEALTHY")
        return 0
    else:
        print("⚠️  Overall Status: NEEDS ATTENTION")
        return 1

if __name__ == "__main__":
    sys.exit(main())
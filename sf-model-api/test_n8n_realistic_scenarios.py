#!/usr/bin/env python3
"""
N8N Realistic Scenarios Test Suite
==================================

Test realistic n8n scenarios to ensure the XML parsing fix works
in actual n8n workflow conditions with various edge cases.
"""

import json
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tool_schemas import parse_tool_calls_from_response, _validate_tool_call_compliance

def test_n8n_http_request_scenario():
    """Test n8n HTTP Request node scenario"""
    print("🧪 Testing n8n HTTP Request scenario...")
    
    response = """
    I'll make the HTTP request for you.
    
    <function_calls>
    {
        "name": "HTTP_Request",
        "arguments": {
            "method": "POST",
            "url": "https://api.example.com/v1/users",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer token123",
                "User-Agent": "n8n-workflow/1.0"
            },
            "body": {
                "name": "John Doe",
                "email": "john@example.com",
                "metadata": {
                    "source": "n8n_workflow",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }
    }
    </function_calls>
    
    Executing HTTP request...
    """
    
    try:
        calls = parse_tool_calls_from_response(response)
        
        if len(calls) != 1:
            print(f"❌ Expected 1 call, got {len(calls)}")
            return False
            
        call = calls[0]
        
        if not _validate_tool_call_compliance(call):
            print("❌ Call not OpenAI compliant")
            return False
            
        args = json.loads(call['function']['arguments'])
        
        # Verify nested structure
        if not isinstance(args.get('headers'), dict):
            print("❌ Headers not parsed as dict")
            return False
            
        if not isinstance(args.get('body'), dict):
            print("❌ Body not parsed as dict")
            return False
            
        if not isinstance(args['body'].get('metadata'), dict):
            print("❌ Nested metadata not parsed as dict")
            return False
            
        print("✅ n8n HTTP Request scenario - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ n8n HTTP Request scenario failed: {e}")
        return False

def test_n8n_email_scenario():
    """Test n8n Email Send node scenario"""
    print("🧪 Testing n8n Email Send scenario...")
    
    response = """
    I'll send the email for you.
    
    <function_calls>
    {
        "name": "Send_Email",
        "arguments": {
            "to": "user@example.com",
            "cc": ["manager@example.com", "team@example.com"],
            "bcc": [],
            "subject": "Automated Report - {{ new Date().toISOString() }}",
            "html": "<h1>Report</h1><p>Data: {{ $json.data }}</p>",
            "attachments": [
                {
                    "filename": "report.pdf",
                    "content": "base64encodedcontent"
                }
            ]
        }
    }
    </function_calls>
    
    Sending email now...
    """
    
    try:
        calls = parse_tool_calls_from_response(response)
        
        if len(calls) != 1:
            print(f"❌ Expected 1 call, got {len(calls)}")
            return False
            
        call = calls[0]
        
        if not _validate_tool_call_compliance(call):
            print("❌ Call not OpenAI compliant")
            return False
            
        args = json.loads(call['function']['arguments'])
        
        # Verify array handling
        if not isinstance(args.get('cc'), list):
            print("❌ CC not parsed as list")
            return False
            
        if not isinstance(args.get('attachments'), list):
            print("❌ Attachments not parsed as list")
            return False
            
        if len(args['attachments']) > 0 and not isinstance(args['attachments'][0], dict):
            print("❌ Attachment items not parsed as dict")
            return False
            
        print("✅ n8n Email Send scenario - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ n8n Email Send scenario failed: {e}")
        return False

def test_n8n_database_scenario():
    """Test n8n Database node scenario"""
    print("🧪 Testing n8n Database scenario...")
    
    response = """
    I'll execute the database query.
    
    <function_calls>
    {
        "name": "Execute_SQL",
        "arguments": {
            "query": "INSERT INTO users (name, email, created_at, metadata) VALUES (?, ?, NOW(), ?)",
            "parameters": ["John Doe", "john@example.com", "{\\"source\\": \\"api\\", \\"tags\\": [\\"new\\", \\"customer\\"]}"],
            "database": "production",
            "timeout": 30000,
            "returnFields": ["id", "name", "email", "created_at"],
            "options": {
                "autoCommit": true,
                "isolation": "READ_COMMITTED"
            }
        }
    }
    </function_calls>
    
    Executing SQL query...
    """
    
    try:
        calls = parse_tool_calls_from_response(response)
        
        if len(calls) != 1:
            print(f"❌ Expected 1 call, got {len(calls)}")
            return False
            
        call = calls[0]
        
        if not _validate_tool_call_compliance(call):
            print("❌ Call not OpenAI compliant")
            return False
            
        args = json.loads(call['function']['arguments'])
        
        # Verify parameter types
        if not isinstance(args.get('parameters'), list):
            print("❌ Parameters not parsed as list")
            return False
            
        if not isinstance(args.get('returnFields'), list):
            print("❌ ReturnFields not parsed as list")
            return False
            
        if not isinstance(args.get('options'), dict):
            print("❌ Options not parsed as dict")
            return False
            
        if not isinstance(args.get('timeout'), int):
            print("❌ Timeout not parsed as int")
            return False
            
        print("✅ n8n Database scenario - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ n8n Database scenario failed: {e}")
        return False

def test_n8n_webhook_scenario():
    """Test n8n Webhook response scenario"""
    print("🧪 Testing n8n Webhook scenario...")
    
    response = """
    I'll send the webhook response.
    
    <function_calls>
    {
        "name": "Webhook_Response",
        "arguments": {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-Custom-Header": "n8n-processed"
            },
            "body": {
                "success": true,
                "message": "Data processed successfully",
                "data": {
                    "processedItems": 42,
                    "errors": [],
                    "processing_time_ms": 1250,
                    "batch_id": "batch_20240115_103000"
                },
                "metadata": {
                    "workflow_id": "wf_12345",
                    "execution_id": "exec_67890",
                    "timestamp": "2024-01-15T10:30:00.000Z"
                }
            }
        }
    }
    </function_calls>
    
    Sending webhook response...
    """
    
    try:
        calls = parse_tool_calls_from_response(response)
        
        if len(calls) != 1:
            print(f"❌ Expected 1 call, got {len(calls)}")
            return False
            
        call = calls[0]
        
        if not _validate_tool_call_compliance(call):
            print("❌ Call not OpenAI compliant")
            return False
            
        args = json.loads(call['function']['arguments'])
        
        # Verify complex nested structure
        if not isinstance(args.get('body'), dict):
            print("❌ Body not parsed as dict")
            return False
            
        if not isinstance(args['body'].get('data'), dict):
            print("❌ Nested data not parsed as dict")
            return False
            
        if not isinstance(args['body']['data'].get('errors'), list):
            print("❌ Errors array not parsed as list")
            return False
            
        if not isinstance(args['body'].get('metadata'), dict):
            print("❌ Metadata not parsed as dict")
            return False
            
        print("✅ n8n Webhook scenario - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ n8n Webhook scenario failed: {e}")
        return False

def test_n8n_code_execution_scenario():
    """Test n8n Code node scenario"""
    print("🧪 Testing n8n Code execution scenario...")
    
    response = """
    I'll execute the JavaScript code.
    
    <function_calls>
    {
        "name": "Execute_JavaScript",
        "arguments": {
            "code": "const data = $input.all(); const processed = data.map(item => ({ ...item, processed: true, timestamp: new Date().toISOString() })); return processed;",
            "sandbox": {
                "timeout": 5000,
                "memory_limit": "128MB",
                "allowed_modules": ["crypto", "uuid", "moment"]
            },
            "context": {
                "workflow_vars": {
                    "batch_size": 100,
                    "max_retries": 3
                },
                "environment": "production"
            },
            "return_type": "json"
        }
    }
    </function_calls>
    
    Running JavaScript code...
    """
    
    try:
        calls = parse_tool_calls_from_response(response)
        
        if len(calls) != 1:
            print(f"❌ Expected 1 call, got {len(calls)}")
            return False
            
        call = calls[0]
        
        if not _validate_tool_call_compliance(call):
            print("❌ Call not OpenAI compliant")
            return False
            
        args = json.loads(call['function']['arguments'])
        
        # Verify code parameter
        if not isinstance(args.get('code'), str):
            print("❌ Code not parsed as string")
            return False
            
        if not isinstance(args.get('sandbox'), dict):
            print("❌ Sandbox not parsed as dict")
            return False
            
        if not isinstance(args['sandbox'].get('allowed_modules'), list):
            print("❌ Allowed modules not parsed as list")
            return False
            
        if not isinstance(args.get('context'), dict):
            print("❌ Context not parsed as dict")
            return False
            
        print("✅ n8n Code execution scenario - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ n8n Code execution scenario failed: {e}")
        return False

def test_n8n_complex_workflow_scenario():
    """Test complex n8n workflow with multiple data types"""
    print("🧪 Testing complex n8n workflow scenario...")
    
    response = """
    I'll process this complex workflow step.
    
    <function_calls>
    {
        "name": "Process_Workflow_Data",
        "arguments": {
            "input_data": [
                {"id": 1, "name": "Item 1", "value": 100.50, "active": true},
                {"id": 2, "name": "Item 2", "value": 250.75, "active": false},
                {"id": 3, "name": "Item 3", "value": 75.25, "active": true}
            ],
            "filters": {
                "active_only": true,
                "min_value": 80.0,
                "categories": ["electronics", "books", "clothing"],
                "date_range": {
                    "start": "2024-01-01T00:00:00Z",
                    "end": "2024-12-31T23:59:59Z"
                }
            },
            "processing_options": {
                "sort_by": "value",
                "sort_order": "desc",
                "limit": 100,
                "include_metadata": true,
                "transformations": [
                    {"type": "currency_conversion", "from": "USD", "to": "EUR"},
                    {"type": "add_field", "field": "processed_at", "value": "{{ $now }}"}
                ]
            },
            "output_format": {
                "type": "json",
                "pretty": false,
                "include_totals": true,
                "group_by": ["category", "active"]
            }
        }
    }
    </function_calls>
    
    Processing complex workflow data...
    """
    
    try:
        calls = parse_tool_calls_from_response(response)
        
        if len(calls) != 1:
            print(f"❌ Expected 1 call, got {len(calls)}")
            return False
            
        call = calls[0]
        
        if not _validate_tool_call_compliance(call):
            print("❌ Call not OpenAI compliant")
            return False
            
        args = json.loads(call['function']['arguments'])
        
        # Verify complex data structures
        if not isinstance(args.get('input_data'), list):
            print("❌ Input data not parsed as list")
            return False
            
        if len(args['input_data']) != 3:
            print(f"❌ Expected 3 input items, got {len(args['input_data'])}")
            return False
            
        # Check data types in array items
        first_item = args['input_data'][0]
        if not isinstance(first_item.get('id'), int):
            print("❌ Item ID not parsed as int")
            return False
            
        if not isinstance(first_item.get('value'), float):
            print("❌ Item value not parsed as float")
            return False
            
        if not isinstance(first_item.get('active'), bool):
            print("❌ Item active not parsed as boolean")
            return False
            
        # Verify nested structures
        if not isinstance(args.get('filters'), dict):
            print("❌ Filters not parsed as dict")
            return False
            
        if not isinstance(args['filters'].get('categories'), list):
            print("❌ Categories not parsed as list")
            return False
            
        if not isinstance(args['filters'].get('date_range'), dict):
            print("❌ Date range not parsed as dict")
            return False
            
        if not isinstance(args.get('processing_options'), dict):
            print("❌ Processing options not parsed as dict")
            return False
            
        if not isinstance(args['processing_options'].get('transformations'), list):
            print("❌ Transformations not parsed as list")
            return False
            
        print("✅ n8n Complex workflow scenario - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ n8n Complex workflow scenario failed: {e}")
        return False

def main():
    """Run all realistic n8n scenarios"""
    print("🚀 N8N Realistic Scenarios Test Suite")
    print("=" * 60)
    print("Testing various real-world n8n tool calling scenarios...")
    print()
    
    tests = [
        test_n8n_http_request_scenario,
        test_n8n_email_scenario,
        test_n8n_database_scenario,
        test_n8n_webhook_scenario,
        test_n8n_code_execution_scenario,
        test_n8n_complex_workflow_scenario
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All realistic n8n scenarios PASSED!")
        print("   Your XML parsing fix handles real-world n8n use cases correctly.")
    else:
        print("⚠️  Some scenarios failed. Review the output above.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
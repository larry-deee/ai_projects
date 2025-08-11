#!/usr/bin/env python3
"""
N8N Tool Calling Fix Demonstration
==================================

This script demonstrates the XML parsing fix for n8n tool calling integration.
It shows the before/after behavior and validates that the fix resolves the
original issue with single object XML function calls.

The Issue:
- n8n was sending XML function calls in single object format: {"name": "func", "arguments": {...}}
- The parser only handled array format: [{"name": "func", "arguments": {...}}]
- This caused n8n tool calls to fail

The Fix:
- Enhanced parse_tool_calls_from_response() to handle both formats
- Single objects are automatically wrapped in an array for consistent processing
- Maintains backward compatibility with existing array format

This demonstration proves the fix is working correctly.
"""

import json
import sys
import os
from typing import Dict, Any, List

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tool_schemas import parse_tool_calls_from_response, _validate_tool_call_compliance

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(title: str):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN} {title.center(76)} {Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_info(message: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_code_block(title: str, content: str):
    """Print formatted code block"""
    print(f"{Colors.YELLOW}{Colors.BOLD}{title}:{Colors.END}")
    print(f"{Colors.MAGENTA}{'─' * 60}{Colors.END}")
    for line in content.strip().split('\n'):
        print(f"{Colors.MAGENTA}│{Colors.END} {line}")
    print(f"{Colors.MAGENTA}{'─' * 60}{Colors.END}")

def demonstrate_single_object_fix():
    """Demonstrate the single object XML parsing fix"""
    print_header("SINGLE OBJECT XML PARSING FIX DEMONSTRATION")
    
    print_info("Before the fix, this format would FAIL:")
    
    # The problematic format that was failing
    single_object_xml = '''
    <function_calls>
    {
        "name": "Research_Agent",
        "arguments": {
            "topic": "artificial intelligence",
            "depth": "comprehensive", 
            "sources": ["academic", "industry"]
        }
    }
    </function_calls>
    '''
    
    print_code_block("Problematic Single Object Format", single_object_xml)
    
    print_info("After the fix, this format now WORKS:")
    
    try:
        parsed_calls = parse_tool_calls_from_response(single_object_xml)
        
        if len(parsed_calls) == 1:
            call = parsed_calls[0]
            
            if _validate_tool_call_compliance(call):
                print_success("✅ Single object XML successfully parsed!")
                print(f"   📋 Function: {call['function']['name']}")
                print(f"   🆔 Call ID: {call['id']}")
                print(f"   ✅ OpenAI Compliant: YES")
                
                args = json.loads(call['function']['arguments'])
                print(f"   📝 Arguments: {len(args)} parameters")
                for key, value in args.items():
                    print(f"      • {key}: {value}")
                
                return True
            else:
                print(f"{Colors.RED}❌ Parsed but not OpenAI compliant{Colors.END}")
                return False
        else:
            print(f"{Colors.RED}❌ Expected 1 call, got {len(parsed_calls)}{Colors.END}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}❌ Parsing failed: {str(e)}{Colors.END}")
        return False

def demonstrate_array_format_compatibility():
    """Demonstrate that array format still works (backward compatibility)"""
    print_header("ARRAY FORMAT BACKWARD COMPATIBILITY")
    
    print_info("The original array format still works perfectly:")
    
    array_format_xml = '''
    <function_calls>
    [
        {
            "name": "Get_Weather",
            "arguments": {
                "location": "San Francisco",
                "units": "celsius"
            }
        },
        {
            "name": "Send_Email", 
            "arguments": {
                "to": "user@example.com",
                "subject": "Weather Update"
            }
        }
    ]
    </function_calls>
    '''
    
    print_code_block("Array Format (Backward Compatible)", array_format_xml)
    
    try:
        parsed_calls = parse_tool_calls_from_response(array_format_xml)
        
        if len(parsed_calls) == 2:
            print_success(f"✅ Array format works! Parsed {len(parsed_calls)} calls")
            
            for i, call in enumerate(parsed_calls):
                if _validate_tool_call_compliance(call):
                    print(f"   📋 Call {i+1}: {call['function']['name']} ✅")
                else:
                    print(f"   📋 Call {i+1}: {call['function']['name']} ❌ (not compliant)")
                    return False
            
            return True
        else:
            print(f"{Colors.RED}❌ Expected 2 calls, got {len(parsed_calls)}{Colors.END}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}❌ Array parsing failed: {str(e)}{Colors.END}")
        return False

def demonstrate_n8n_real_scenario():
    """Demonstrate a realistic n8n scenario"""
    print_header("REALISTIC N8N WORKFLOW SCENARIO")
    
    print_info("Testing a real n8n OpenAI Chat Model node scenario:")
    
    n8n_scenario = '''
    I'll help you process that data through the API.
    
    <function_calls>
    {
        "name": "n8n_HTTP_Request",
        "arguments": {
            "method": "POST",
            "url": "https://api.example.com/v1/process",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer {{ $node.parameter.apiKey }}",
                "X-Source": "n8n-workflow"
            },
            "body": {
                "data": "{{ $json.input_data }}",
                "processing_options": {
                    "format": "json",
                    "validate": true,
                    "timeout": 30
                }
            }
        }
    }
    </function_calls>
    
    Processing your request through the API...
    '''
    
    print_code_block("N8N OpenAI Chat Model Node Output", n8n_scenario)
    
    try:
        parsed_calls = parse_tool_calls_from_response(n8n_scenario)
        
        if len(parsed_calls) == 1:
            call = parsed_calls[0]
            
            if _validate_tool_call_compliance(call):
                print_success("✅ N8N scenario works perfectly!")
                
                args = json.loads(call['function']['arguments'])
                
                print(f"   📋 Function: {call['function']['name']}")
                print(f"   🌐 Method: {args['method']}")
                print(f"   🔗 URL: {args['url']}")
                print(f"   📄 Headers: {len(args['headers'])} defined")
                print(f"   📦 Body structure: {len(args['body'])} properties")
                print(f"   ✅ OpenAI Compliant: YES")
                
                return True
            else:
                print(f"{Colors.RED}❌ Not OpenAI compliant{Colors.END}")
                return False
        else:
            print(f"{Colors.RED}❌ Expected 1 call, got {len(parsed_calls)}{Colors.END}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}❌ N8N scenario failed: {str(e)}{Colors.END}")
        return False

def demonstrate_complete_pipeline():
    """Demonstrate the complete tool calling pipeline"""
    print_header("COMPLETE TOOL CALLING PIPELINE DEMONSTRATION")
    
    print_info("Testing the complete pipeline: XML → Parse → OpenAI Format → Validation")
    
    pipeline_test = '''
    <function_calls>
    {
        "name": "Data_Processor",
        "arguments": {
            "input": [{"id": 1, "value": 100}, {"id": 2, "value": 200}],
            "operation": "sum",
            "options": {
                "format": "json",
                "precision": 2,
                "include_metadata": true
            }
        }
    }
    </function_calls>
    '''
    
    print_code_block("Pipeline Test Input", pipeline_test)
    
    try:
        # Step 1: Parse XML  
        print("   🔄 Step 1: Parsing XML...")
        parsed_calls = parse_tool_calls_from_response(pipeline_test)
        print(f"      ✅ Parsed {len(parsed_calls)} tool call(s)")
        
        if len(parsed_calls) != 1:
            print(f"      ❌ Expected 1 call, got {len(parsed_calls)}")
            return False
        
        call = parsed_calls[0]
        
        # Step 2: Validate OpenAI compliance
        print("   🔄 Step 2: Validating OpenAI compliance...")
        if _validate_tool_call_compliance(call):
            print("      ✅ Call is OpenAI compliant")
        else:
            print("      ❌ Call is not OpenAI compliant")
            return False
        
        # Step 3: Parse arguments
        print("   🔄 Step 3: Parsing arguments...")
        args = json.loads(call['function']['arguments'])
        print(f"      ✅ Parsed {len(args)} arguments successfully")
        
        # Step 4: Validate data types
        print("   🔄 Step 4: Validating data types...")
        
        if isinstance(args.get('input'), list):
            print("      ✅ Input parsed as array")
        else:
            print("      ❌ Input not parsed as array")
            return False
            
        if isinstance(args.get('options'), dict):
            print("      ✅ Options parsed as object")
        else:
            print("      ❌ Options not parsed as object")
            return False
        
        # Step 5: Final structure verification
        print("   🔄 Step 5: Final structure verification...")
        
        required_fields = ['id', 'type', 'function']
        for field in required_fields:
            if field in call:
                print(f"      ✅ Required field '{field}' present")
            else:
                print(f"      ❌ Required field '{field}' missing")
                return False
        
        print_success("🎉 Complete pipeline successful!")
        print(f"   📋 Final call structure:")
        print(f"      • ID: {call['id']}")
        print(f"      • Type: {call['type']}") 
        print(f"      • Function: {call['function']['name']}")
        print(f"      • Arguments: {len(args)} parameters")
        
        return True
        
    except Exception as e:
        print(f"{Colors.RED}❌ Pipeline failed: {str(e)}{Colors.END}")
        return False

def print_summary(results: List[bool]):
    """Print final summary"""
    print_header("DEMONSTRATION SUMMARY")
    
    test_names = [
        "Single Object XML Parsing Fix",
        "Array Format Backward Compatibility", 
        "Realistic N8N Workflow Scenario",
        "Complete Tool Calling Pipeline"
    ]
    
    passed = sum(results)
    total = len(results)
    
    print(f"{Colors.BOLD}Test Results:{Colors.END}")
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = f"{Colors.GREEN}✅ PASS{Colors.END}" if result else f"{Colors.RED}❌ FAIL{Colors.END}"
        print(f"  {i+1}. {name}: {status}")
    
    print(f"\n{Colors.BOLD}Overall: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED!{Colors.END}")
        print(f"{Colors.GREEN}✅ The XML parsing fix is working correctly{Colors.END}")
        print(f"{Colors.GREEN}✅ N8N tool calling integration is fully functional{Colors.END}")
        print(f"{Colors.GREEN}✅ Both single object and array formats are supported{Colors.END}")
        print(f"{Colors.GREEN}✅ Complete pipeline from XML to OpenAI format works{Colors.END}")
        
        print(f"\n{Colors.CYAN}{Colors.BOLD}🚀 NEXT STEPS:{Colors.END}")
        print(f"1. Test with your actual n8n workflow")
        print(f"2. Use the validation script: {Colors.BOLD}python validate_n8n_fix.py{Colors.END}")
        print(f"3. The fix is ready for production use")
        
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  SOME TESTS FAILED{Colors.END}")
        print(f"{Colors.YELLOW}Please review the failed tests above{Colors.END}")

def main():
    """Run the complete demonstration"""
    print(f"{Colors.BOLD}{Colors.CYAN}N8N Tool Calling Fix Demonstration{Colors.END}")
    print(f"{Colors.CYAN}Verifying that the XML parsing fix resolves the n8n integration issue{Colors.END}")
    
    # Run all demonstrations
    results = []
    
    results.append(demonstrate_single_object_fix())
    results.append(demonstrate_array_format_compatibility()) 
    results.append(demonstrate_n8n_real_scenario())
    results.append(demonstrate_complete_pipeline())
    
    # Print summary
    print_summary(results)
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
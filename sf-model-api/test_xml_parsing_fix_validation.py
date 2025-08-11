#!/usr/bin/env python3
"""
XML Parsing Fix Validation Test Suite
=====================================

Comprehensive test suite to verify the XML function call parsing fix
is working correctly for n8n tool calling integration.

This test validates:
1. Single object XML format: {"name": "func", "arguments": {...}}
2. Array format XML: [{"name": "func", "arguments": {...}}]
3. Complete pipeline from XML to OpenAI format
4. n8n specific edge cases and scenarios
5. Error handling and recovery mechanisms
"""

import json
import sys
import os
import uuid
from typing import Dict, Any, List

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tool_schemas import (
    parse_tool_calls_from_response,
    _create_openai_compliant_tool_call,
    _validate_tool_call_compliance,
    create_tool_call_id
)

class Colors:
    """ANSI color codes for test output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_header(title: str):
    """Print formatted test section header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN} {title.center(76)} {Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

def print_test(test_name: str, success: bool, details: str = ""):
    """Print formatted test result"""
    status = f"{Colors.GREEN}✅ PASS{Colors.END}" if success else f"{Colors.RED}❌ FAIL{Colors.END}"
    print(f"{status} {Colors.BOLD}{test_name}{Colors.END}")
    if details:
        print(f"     {Colors.YELLOW}{details}{Colors.END}")

def print_info(message: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}🚨 {message}{Colors.END}")

class XMLParsingFixValidator:
    """Comprehensive validator for the XML parsing fix"""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
    
    def run_test(self, test_name: str, test_func, *args, **kwargs):
        """Run a single test and track results"""
        try:
            success, details = test_func(*args, **kwargs)
            if success:
                self.tests_passed += 1
                print_test(test_name, True, details)
            else:
                self.tests_failed += 1
                print_test(test_name, False, details)
            
            self.test_results.append({
                'name': test_name,
                'success': success,
                'details': details
            })
            return success
            
        except Exception as e:
            self.tests_failed += 1
            error_details = f"Exception: {str(e)}"
            print_test(test_name, False, error_details)
            self.test_results.append({
                'name': test_name,
                'success': False,
                'details': error_details
            })
            return False
    
    def test_single_object_xml_parsing(self):
        """Test parsing of single object XML format"""
        # Single object format that was previously failing
        response_text = '''
        I'll help you research that topic.
        
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
        
        Let me search for the latest information.
        '''
        
        try:
            parsed_calls = parse_tool_calls_from_response(response_text)
            
            if len(parsed_calls) != 1:
                return False, f"Expected 1 tool call, got {len(parsed_calls)}"
            
            call = parsed_calls[0]
            
            # Verify OpenAI compliance
            if not _validate_tool_call_compliance(call):
                return False, "Tool call is not OpenAI compliant"
            
            # Verify structure
            if call['function']['name'] != 'Research_Agent':
                return False, f"Expected function name 'Research_Agent', got '{call['function']['name']}'"
            
            # Verify arguments
            args = json.loads(call['function']['arguments'])
            if args['topic'] != 'artificial intelligence':
                return False, f"Expected topic 'artificial intelligence', got '{args['topic']}'"
            
            return True, f"Successfully parsed single object XML with ID: {call['id']}"
            
        except Exception as e:
            return False, f"Parsing failed: {str(e)}"
    
    def test_array_format_xml_parsing(self):
        """Test parsing of array format XML (original working format)"""
        response_text = '''
        I'll help you with both tasks.
        
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
                    "subject": "Weather Update",
                    "body": "Here's your weather update"
                }
            }
        ]
        </function_calls>
        
        I'll execute these functions for you.
        '''
        
        try:
            parsed_calls = parse_tool_calls_from_response(response_text)
            
            if len(parsed_calls) != 2:
                return False, f"Expected 2 tool calls, got {len(parsed_calls)}"
            
            # Verify both calls are OpenAI compliant
            for i, call in enumerate(parsed_calls):
                if not _validate_tool_call_compliance(call):
                    return False, f"Tool call {i} is not OpenAI compliant"
            
            # Verify first call
            first_call = parsed_calls[0]
            if first_call['function']['name'] != 'Get_Weather':
                return False, f"Expected first function 'Get_Weather', got '{first_call['function']['name']}'"
            
            # Verify second call
            second_call = parsed_calls[1]
            if second_call['function']['name'] != 'Send_Email':
                return False, f"Expected second function 'Send_Email', got '{second_call['function']['name']}'"
            
            return True, f"Successfully parsed array format XML with {len(parsed_calls)} calls"
            
        except Exception as e:
            return False, f"Parsing failed: {str(e)}"
    
    def test_mixed_format_handling(self):
        """Test handling of various XML formats in sequence"""
        test_cases = [
            # Single object
            '<function_calls>{"name": "test1", "arguments": {"param": "value1"}}</function_calls>',
            # Array with one item
            '<function_calls>[{"name": "test2", "arguments": {"param": "value2"}}]</function_calls>',
            # Array with multiple items
            '<function_calls>[{"name": "test3", "arguments": {"param": "value3"}}, {"name": "test4", "arguments": {"param": "value4"}}]</function_calls>'
        ]
        
        expected_counts = [1, 1, 2]
        
        for i, (test_case, expected_count) in enumerate(zip(test_cases, expected_counts)):
            try:
                parsed_calls = parse_tool_calls_from_response(test_case)
                
                if len(parsed_calls) != expected_count:
                    return False, f"Test case {i+1}: Expected {expected_count} calls, got {len(parsed_calls)}"
                
                # Verify all calls are compliant
                for call in parsed_calls:
                    if not _validate_tool_call_compliance(call):
                        return False, f"Test case {i+1}: Non-compliant tool call"
                        
            except Exception as e:
                return False, f"Test case {i+1} failed: {str(e)}"
        
        return True, f"Successfully handled {len(test_cases)} different XML formats"
    
    def test_n8n_specific_scenarios(self):
        """Test n8n-specific tool call scenarios"""
        # n8n often sends single function calls with automatic parameters
        n8n_response = '''
        I'll process that request for you.
        
        <function_calls>
        {
            "name": "n8n_HTTP_Request",
            "arguments": {
                "url": "https://api.example.com/data",
                "method": "GET",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer token123"
                }
            }
        }
        </function_calls>
        
        Processing your HTTP request now.
        '''
        
        try:
            parsed_calls = parse_tool_calls_from_response(n8n_response)
            
            if len(parsed_calls) != 1:
                return False, f"Expected 1 n8n tool call, got {len(parsed_calls)}"
            
            call = parsed_calls[0]
            
            # Verify OpenAI compliance
            if not _validate_tool_call_compliance(call):
                return False, "n8n tool call is not OpenAI compliant"
            
            # Verify function name
            if call['function']['name'] != 'n8n_HTTP_Request':
                return False, f"Expected 'n8n_HTTP_Request', got '{call['function']['name']}'"
            
            # Verify nested arguments structure
            args = json.loads(call['function']['arguments'])
            if 'headers' not in args or not isinstance(args['headers'], dict):
                return False, "Missing or invalid headers in n8n arguments"
            
            return True, f"Successfully processed n8n scenario with nested arguments"
            
        except Exception as e:
            return False, f"n8n scenario failed: {str(e)}"
    
    def test_error_recovery(self):
        """Test error recovery mechanisms"""
        # Malformed JSON that should trigger recovery
        malformed_cases = [
            # Extra closing bracket
            '<function_calls>{"name": "test", "arguments": {"param": "value"}}]</function_calls>',
            # Missing opening bracket
            '<function_calls>"name": "test", "arguments": {"param": "value"}}</function_calls>',
            # Trailing comma
            '<function_calls>{"name": "test", "arguments": {"param": "value",}}</function_calls>'
        ]
        
        recovered_count = 0
        for i, malformed_case in enumerate(malformed_cases):
            try:
                parsed_calls = parse_tool_calls_from_response(malformed_case)
                if len(parsed_calls) > 0:
                    recovered_count += 1
                    # Verify recovery produced compliant calls
                    for call in parsed_calls:
                        if not _validate_tool_call_compliance(call):
                            return False, f"Recovery case {i+1}: Non-compliant recovered call"
            except:
                # Recovery failure is acceptable for some cases
                continue
        
        if recovered_count > 0:
            return True, f"Successfully recovered {recovered_count}/{len(malformed_cases)} malformed cases"
        else:
            return False, "No malformed cases were successfully recovered"
    
    def test_openai_compliance_validation(self):
        """Test OpenAI compliance validation"""
        # Test valid OpenAI format
        valid_call = {
            "id": "call_abc123",
            "type": "function",
            "function": {
                "name": "test_function",
                "arguments": '{"param1": "value1", "param2": 42}'
            }
        }
        
        if not _validate_tool_call_compliance(valid_call):
            return False, "Valid OpenAI call failed compliance check"
        
        # Test invalid formats
        invalid_cases = [
            # Missing ID
            {"type": "function", "function": {"name": "test", "arguments": "{}"}},
            # Wrong type
            {"id": "call_123", "type": "invalid", "function": {"name": "test", "arguments": "{}"}},
            # Missing function
            {"id": "call_123", "type": "function"},
            # Arguments not a string
            {"id": "call_123", "type": "function", "function": {"name": "test", "arguments": {}}},
        ]
        
        for i, invalid_call in enumerate(invalid_cases):
            if _validate_tool_call_compliance(invalid_call):
                return False, f"Invalid case {i+1} incorrectly passed compliance check"
        
        return True, f"Compliance validation correctly identified valid and invalid formats"
    
    def test_complete_pipeline(self):
        """Test the complete pipeline from XML to OpenAI format"""
        # Simulate a complete n8n scenario
        xml_response = '''
        I'll help you with that task. Let me call the appropriate function.
        
        <function_calls>
        {
            "name": "Process_Data",
            "arguments": {
                "input_data": [1, 2, 3, 4, 5],
                "operation": "sum",
                "output_format": "json",
                "metadata": {
                    "source": "user_input",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
            }
        }
        </function_calls>
        
        Processing your data now...
        '''
        
        try:
            # Step 1: Parse XML
            parsed_calls = parse_tool_calls_from_response(xml_response)
            
            if len(parsed_calls) != 1:
                return False, f"Pipeline step 1 failed: Expected 1 call, got {len(parsed_calls)}"
            
            # Step 2: Verify OpenAI compliance
            call = parsed_calls[0]
            if not _validate_tool_call_compliance(call):
                return False, "Pipeline step 2 failed: Call not OpenAI compliant"
            
            # Step 3: Test argument parsing
            args = json.loads(call['function']['arguments'])
            
            # Verify complex nested structure
            if not isinstance(args.get('input_data'), list):
                return False, "Pipeline step 3 failed: input_data not parsed as list"
            
            if not isinstance(args.get('metadata'), dict):
                return False, "Pipeline step 3 failed: metadata not parsed as dict"
            
            # Step 4: Verify all required fields
            required_fields = ['input_data', 'operation', 'output_format', 'metadata']
            missing_fields = [field for field in required_fields if field not in args]
            
            if missing_fields:
                return False, f"Pipeline step 4 failed: Missing fields {missing_fields}"
            
            # Step 5: Test call structure
            if not call['id'].startswith('call_'):
                return False, f"Pipeline step 5 failed: Invalid ID format '{call['id']}'"
            
            return True, f"Complete pipeline successful: {call['function']['name']} with {len(args)} arguments"
            
        except Exception as e:
            return False, f"Pipeline failed with exception: {str(e)}"
    
    def create_user_validation_script(self):
        """Create a simple validation script for the user"""
        script_content = '''#!/usr/bin/env python3
"""
N8N Tool Calling Validation Script
==================================

Simple validation script to test that your n8n tool calling issue is resolved.
Run this script to verify the XML parsing fix is working correctly.
"""

import sys
import os
import json

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from tool_schemas import parse_tool_calls_from_response, _validate_tool_call_compliance
except ImportError:
    print("❌ Error: Could not import tool_schemas module")
    print("   Make sure you're running this from the project root directory")
    sys.exit(1)

def test_n8n_fix():
    """Test the n8n XML parsing fix"""
    print("🔧 Testing n8n XML Function Call Parsing Fix...")
    print("=" * 60)
    
    # Test the problematic single object format
    test_response = \\"""
    I'll help you with that request.
    
    <function_calls>
    {
        "name": "Research_Agent",
        "arguments": {
            "topic": "machine learning",
            "depth": "detailed",
            "sources": ["academic", "industry", "news"]
        }
    }
    </function_calls>
    
    Let me search for information on this topic.
    \\"""
    
    try:
        # Parse the response
        parsed_calls = parse_tool_calls_from_response(test_response)
        
        if len(parsed_calls) == 0:
            print("❌ FAILED: No tool calls were parsed")
            return False
        
        if len(parsed_calls) != 1:
            print(f"❌ FAILED: Expected 1 tool call, got {len(parsed_calls)}")
            return False
        
        call = parsed_calls[0]
        
        # Verify OpenAI compliance
        if not _validate_tool_call_compliance(call):
            print("❌ FAILED: Tool call is not OpenAI compliant")
            return False
        
        # Verify function details
        if call['function']['name'] != 'Research_Agent':
            print(f"❌ FAILED: Expected function name 'Research_Agent', got '{call['function']['name']}'")
            return False
        
        # Verify arguments
        args = json.loads(call['function']['arguments'])
        if args.get('topic') != 'machine learning':
            print(f"❌ FAILED: Expected topic 'machine learning', got '{args.get('topic')}'")
            return False
        
        print("✅ SUCCESS: XML parsing fix is working correctly!")
        print(f"   - Function: {call['function']['name']}")
        print(f"   - Call ID: {call['id']}")
        print(f"   - Arguments: {len(args)} parameters parsed")
        print(f"   - OpenAI Compliant: ✅")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Exception occurred: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_n8n_fix()
    
    print("\\n" + "=" * 60)
    if success:
        print("🎉 Your n8n tool calling issue has been RESOLVED!")
        print("   The XML parsing fix is working correctly.")
        print("   You can now use single object XML function calls in n8n.")
    else:
        print("🚨 The n8n tool calling issue is NOT resolved.")
        print("   Please check the error messages above.")
    
    sys.exit(0 if success else 1)
'''
        
        with open('/Users/Dev/ai_projects/sf-model-api/validate_n8n_fix.py', 'w') as f:
            f.write(script_content)
        
        return True, "Created user validation script: validate_n8n_fix.py"
    
    def run_all_tests(self):
        """Run the complete test suite"""
        print_header("XML PARSING FIX VALIDATION TEST SUITE")
        print_info("Testing the fix for n8n single object XML function call parsing...")
        
        # Run all tests
        print_header("1. SINGLE OBJECT XML PARSING")
        self.run_test("Single Object XML Format", self.test_single_object_xml_parsing)
        
        print_header("2. ARRAY FORMAT XML PARSING")
        self.run_test("Array Format XML (Original)", self.test_array_format_xml_parsing)
        
        print_header("3. MIXED FORMAT HANDLING")
        self.run_test("Multiple XML Formats", self.test_mixed_format_handling)
        
        print_header("4. N8N SPECIFIC SCENARIOS")
        self.run_test("n8n Integration Scenarios", self.test_n8n_specific_scenarios)
        
        print_header("5. ERROR RECOVERY")
        self.run_test("Malformed XML Recovery", self.test_error_recovery)
        
        print_header("6. OPENAI COMPLIANCE")
        self.run_test("OpenAI Format Compliance", self.test_openai_compliance_validation)
        
        print_header("7. COMPLETE PIPELINE")
        self.run_test("End-to-End Pipeline", self.test_complete_pipeline)
        
        print_header("8. USER VALIDATION SCRIPT")
        self.run_test("User Validation Script Creation", self.create_user_validation_script)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        total_tests = self.tests_passed + self.tests_failed
        success_rate = (self.tests_passed / total_tests) * 100 if total_tests > 0 else 0
        
        print_header("TEST SUMMARY")
        
        if self.tests_failed == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED!{Colors.END}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}⚠️  SOME TESTS FAILED{Colors.END}")
        
        print(f"{Colors.BOLD}Total Tests:{Colors.END} {total_tests}")
        print(f"{Colors.GREEN}{Colors.BOLD}Passed:{Colors.END} {self.tests_passed}")
        print(f"{Colors.RED}{Colors.BOLD}Failed:{Colors.END} {self.tests_failed}")
        print(f"{Colors.BLUE}{Colors.BOLD}Success Rate:{Colors.END} {success_rate:.1f}%")
        
        # Print failed tests if any
        if self.tests_failed > 0:
            print(f"\n{Colors.RED}{Colors.BOLD}Failed Tests:{Colors.END}")
            for result in self.test_results:
                if not result['success']:
                    print(f"  {Colors.RED}❌ {result['name']}{Colors.END}: {result['details']}")
        
        print_header("VALIDATION CONCLUSION")
        
        if self.tests_failed == 0:
            print(f"{Colors.GREEN}✅ The XML parsing fix is working correctly!{Colors.END}")
            print(f"{Colors.GREEN}✅ n8n single object XML function calls are now supported{Colors.END}")
            print(f"{Colors.GREEN}✅ Complete pipeline from XML to OpenAI format is functional{Colors.END}")
            print(f"\n{Colors.CYAN}Next steps:{Colors.END}")
            print(f"  1. Run the user validation script: {Colors.BOLD}python validate_n8n_fix.py{Colors.END}")
            print(f"  2. Test with your actual n8n workflow")
            print(f"  3. The fix handles both single object and array XML formats")
        else:
            print(f"{Colors.RED}❌ The XML parsing fix has issues that need attention{Colors.END}")
            print(f"{Colors.YELLOW}⚠️  Review the failed tests above for specific problems{Colors.END}")

def main():
    """Main test runner"""
    validator = XMLParsingFixValidator()
    validator.run_all_tests()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
N8N Tool Calling Regression Prevention Test
===========================================

This test ensures that the n8n tool calling issue we just fixed doesn't regress.
It tests all the edge cases and scenarios that could break n8n compatibility.

KEY ISSUE FIXED:
- XML function calls in single object format {...} were not being parsed
- Only array format [{...}] was supported
- This caused tool calls to not be detected, breaking n8n workflows

RUN THIS TEST AFTER ANY CHANGES TO:
- unified_response_formatter.py
- tool_schemas.py (especially parse_tool_calls_from_response)
- response_normaliser.py
- async_endpoint_server.py (tool calling logic)
"""

import sys
import os
sys.path.append('src')

from unified_response_formatter import UnifiedResponseFormatter
from tool_schemas import parse_tool_calls_from_response
from response_normaliser import normalise_assistant_tool_response
import json

class N8NRegressionTests:
    """Comprehensive test suite for n8n tool calling compatibility."""
    
    def __init__(self):
        self.formatter = UnifiedResponseFormatter(debug_mode=False)
        self.test_results = []
    
    def run_all_tests(self):
        """Run all regression prevention tests."""
        print("🔒 N8N Tool Calling Regression Prevention Tests")
        print("=" * 60)
        
        # Test the specific issue that was fixed
        self.test_single_object_xml_parsing()
        
        # Test edge cases that could cause similar issues
        self.test_mixed_xml_formats()
        self.test_salesforce_response_formats()
        self.test_openai_compliance()
        self.test_n8n_workflow_simulation()
        
        # Report results
        self.report_results()
        
        return all(result[1] for result in self.test_results)
    
    def test_single_object_xml_parsing(self):
        """Test the specific issue that was breaking n8n: single object XML format."""
        test_name = "Single Object XML Parsing (Primary Fix)"
        
        # This is the format that was failing before the fix
        single_object_xml = """<function_calls>
{
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "Test single object format"
 }
}
</function_calls>"""
        
        try:
            # Test direct XML parsing
            tool_calls = parse_tool_calls_from_response(single_object_xml)
            
            # Validate the result
            success = (
                len(tool_calls) == 1 and
                tool_calls[0].get('type') == 'function' and
                tool_calls[0].get('function', {}).get('name') == 'Research_Agent' and
                'id' in tool_calls[0] and
                isinstance(tool_calls[0].get('function', {}).get('arguments'), str)
            )
            
            self.test_results.append((test_name, success))
            print(f"{'✅' if success else '❌'} {test_name}: {'PASS' if success else 'FAIL'}")
            
            if not success:
                print(f"   Details: {len(tool_calls)} calls, format: {tool_calls}")
                
        except Exception as e:
            self.test_results.append((test_name, False))
            print(f"❌ {test_name}: ERROR - {str(e)}")
    
    def test_mixed_xml_formats(self):
        """Test various XML formats to ensure all work correctly."""
        test_cases = [
            ("Array Format", """<function_calls>[{"name": "Test", "arguments": {"msg": "array"}}]</function_calls>"""),
            ("Single Object", """<function_calls>{"name": "Test", "arguments": {"msg": "single"}}</function_calls>"""),
            ("Multiple Objects", """<function_calls>[{"name": "Test1", "arguments": {}}, {"name": "Test2", "arguments": {}}]</function_calls>"""),
            ("Whitespace Heavy", """<function_calls>
    {
        "name": "Test",
        "arguments": {
            "msg": "formatted"
        }
    }
</function_calls>"""),
            ("Compact Format", """<function_calls>{"name":"Test","arguments":{"msg":"compact"}}</function_calls>""")
        ]
        
        for case_name, xml_content in test_cases:
            test_name = f"XML Format: {case_name}"
            
            try:
                tool_calls = parse_tool_calls_from_response(xml_content)
                success = len(tool_calls) > 0
                
                self.test_results.append((test_name, success))
                print(f"{'✅' if success else '❌'} {test_name}: {'PASS' if success else 'FAIL'}")
                
            except Exception as e:
                self.test_results.append((test_name, False))
                print(f"❌ {test_name}: ERROR - {str(e)}")
    
    def test_salesforce_response_formats(self):
        """Test different Salesforce response formats that could contain XML."""
        
        xml_content = """<function_calls>{"name": "TestFunc", "arguments": {"test": true}}</function_calls>"""
        
        response_formats = [
            ("response.generations[0][0].text", {
                "response": {"generations": [[{"text": xml_content}]]}
            }),
            ("generation.generatedText", {
                "generation": {"generatedText": xml_content}
            }),
            ("generation.text", {
                "generation": {"text": xml_content}
            }),
            ("choices[0].message.content", {
                "choices": [{"message": {"content": xml_content}}]
            })
        ]
        
        for format_name, response in response_formats:
            test_name = f"Salesforce Format: {format_name}"
            
            try:
                # Test full pipeline
                openai_response = self.formatter.format_openai_response(response, "test-model")
                
                success = (
                    'choices' in openai_response and
                    len(openai_response['choices']) > 0 and
                    'tool_calls' in openai_response['choices'][0].get('message', {}) and
                    len(openai_response['choices'][0]['message']['tool_calls']) > 0
                )
                
                self.test_results.append((test_name, success))
                print(f"{'✅' if success else '❌'} {test_name}: {'PASS' if success else 'FAIL'}")
                
            except Exception as e:
                self.test_results.append((test_name, False))
                print(f"❌ {test_name}: ERROR - {str(e)}")
    
    def test_openai_compliance(self):
        """Test that all tool calls are OpenAI compliant."""
        test_name = "OpenAI Compliance Validation"
        
        xml_single = """<function_calls>{"name": "TestFunc", "arguments": {"param": "value"}}</function_calls>"""
        
        try:
            tool_calls = parse_tool_calls_from_response(xml_single)
            
            if len(tool_calls) == 0:
                success = False
                print(f"❌ {test_name}: No tool calls parsed")
            else:
                call = tool_calls[0]
                
                # Check OpenAI compliance
                compliance_checks = [
                    ('id field exists', 'id' in call),
                    ('type is function', call.get('type') == 'function'),
                    ('function field exists', 'function' in call),
                    ('function.name exists', 'name' in call.get('function', {})),
                    ('function.arguments is string', isinstance(call.get('function', {}).get('arguments'), str)),
                    ('arguments is valid JSON', self._is_valid_json(call.get('function', {}).get('arguments', '')))
                ]
                
                success = all(check[1] for check in compliance_checks)
                
                if not success:
                    print(f"❌ {test_name}: FAIL")
                    for check_name, passed in compliance_checks:
                        print(f"   {check_name}: {'✅' if passed else '❌'}")
                else:
                    print(f"✅ {test_name}: PASS")
            
            self.test_results.append((test_name, success))
            
        except Exception as e:
            self.test_results.append((test_name, False))
            print(f"❌ {test_name}: ERROR - {str(e)}")
    
    def test_n8n_workflow_simulation(self):
        """Simulate a complete n8n workflow to ensure end-to-end compatibility."""
        test_name = "N8N Workflow Simulation"
        
        # Simulate n8n request
        n8n_request = {
            "model": "sfdc_ai__DefaultGPT4Omni",
            "messages": [{"role": "user", "content": "Research AI trends"}],
            "tools": [{
                "type": "function",
                "function": {
                    "name": "Research_Agent",
                    "description": "Research function",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        },
                        "required": ["query"]
                    }
                }
            }]
        }
        
        # Simulate Salesforce response with single object XML (the problematic format)
        salesforce_response = {
            "generation": {
                "generatedText": """<function_calls>
{
 "name": "Research_Agent", 
 "arguments": {
 "query": "AI trends research"
 }
}
</function_calls>"""
            },
            "tokenUsageEstimate": {"completionTokens": 50, "promptTokens": 100, "totalTokens": 150}
        }
        
        try:
            # Process through the pipeline
            openai_response = self.formatter.format_openai_response(
                salesforce_response, 
                n8n_request['model']
            )
            
            # Check n8n compatibility requirements
            n8n_requirements = [
                ('response has choices', 'choices' in openai_response),
                ('choice has message', 'message' in openai_response.get('choices', [{}])[0]),
                ('message has tool_calls', 'tool_calls' in openai_response.get('choices', [{}])[0].get('message', {})),
                ('tool_calls not empty', len(openai_response.get('choices', [{}])[0].get('message', {}).get('tool_calls', [])) > 0),
                ('finish_reason is tool_calls', openai_response.get('choices', [{}])[0].get('finish_reason') == 'tool_calls'),
                ('content is empty when tool_calls present', openai_response.get('choices', [{}])[0].get('message', {}).get('content') == '')
            ]
            
            success = all(req[1] for req in n8n_requirements)
            
            if success:
                print(f"✅ {test_name}: PASS")
            else:
                print(f"❌ {test_name}: FAIL")
                for req_name, passed in n8n_requirements:
                    print(f"   {req_name}: {'✅' if passed else '❌'}")
            
            self.test_results.append((test_name, success))
            
        except Exception as e:
            self.test_results.append((test_name, False))
            print(f"❌ {test_name}: ERROR - {str(e)}")
    
    def _is_valid_json(self, json_str):
        """Check if a string is valid JSON."""
        try:
            json.loads(json_str)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    def report_results(self):
        """Report final test results."""
        print(f"\n📊 REGRESSION TEST RESULTS")
        print("=" * 60)
        
        passed = sum(1 for _, success in self.test_results if success)
        total = len(self.test_results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if passed == total:
            print(f"\n🎉 ALL TESTS PASSED - N8N compatibility is intact!")
        else:
            print(f"\n⚠️  SOME TESTS FAILED - N8N compatibility may be broken!")
            
            failing_tests = [name for name, success in self.test_results if not success]
            print(f"\nFailing tests:")
            for test in failing_tests:
                print(f"   - {test}")
        
        print(f"\n💡 PREVENTION NOTES:")
        print(f"   - Always test single object XML format: {{\"name\": \"...\", \"arguments\": {{...}}}}")
        print(f"   - Ensure OpenAI compliance: id, type='function', function.name, function.arguments as JSON string")
        print(f"   - Test with different Salesforce response paths")
        print(f"   - Verify n8n workflow compatibility end-to-end")

def main():
    """Run all regression prevention tests."""
    tester = N8NRegressionTests()
    success = tester.run_all_tests()
    
    print(f"\n{'='*60}")
    if success:
        print("✅ ALL REGRESSION TESTS PASSED")
        print("💪 N8N tool calling is protected against regressions!")
    else:
        print("❌ REGRESSION TESTS FAILED")
        print("🚨 N8N tool calling may be broken - investigate immediately!")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
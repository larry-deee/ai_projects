#!/usr/bin/env python3
"""
Test Wikipedia API Parameter Mapping Issue
==========================================

This test reproduces the specific issue with parameter name mismatch:
- Model returns {'input': 'Generative AI'} 
- Function expects 'query' parameter
- Error: wikipedia_api() missing 1 required positional argument: 'query'
"""

import sys
import os
sys.path.append('src')

from tool_executor import ToolExecutor
from tool_schemas import ToolCallingConfig, ToolCall
import json

def test_wikipedia_parameter_mapping_issue():
    """Test the specific wikipedia-api parameter mapping issue."""
    
    print("🔍 Testing Wikipedia API Parameter Mapping Issue")
    print("=" * 60)
    
    # Create tool executor with default config
    config = ToolCallingConfig()
    executor = ToolExecutor(config)
    
    print("📋 Available Functions:")
    for func_name in executor.registry.list_functions():
        print(f"   - {func_name}")
    
    # Check wikipedia function definition
    wiki_def = executor.registry.get_definition("wikipedia-api")
    if wiki_def:
        print(f"\n📝 Wikipedia-API Function Definition:")
        print(f"   - Name: {wiki_def.name}")
        print(f"   - Description: {wiki_def.description}")
        print(f"   - Parameters:")
        for param_name, param_schema in wiki_def.parameters.properties.items():
            required = param_name in (wiki_def.parameters.required or [])
            print(f"     - {param_name} ({param_schema.type.value}): {param_schema.description} {'[REQUIRED]' if required else '[OPTIONAL]'}")
    else:
        print(f"❌ Wikipedia-API function definition not found!")
        return False
    
    # Test the problematic case: model returns 'input' but function expects 'query'
    print(f"\n🧪 Testing Parameter Mapping Issue...")
    
    # Create tool call with 'input' parameter (what model returns)
    problematic_call = ToolCall(
        function={
            "name": "wikipedia-api",
            "arguments": {"input": "Generative AI"}  # WRONG parameter name
        }
    )
    
    print(f"📤 Problematic Tool Call:")
    print(f"   - Function: {problematic_call.function_name}")
    print(f"   - Arguments: {problematic_call.function_arguments}")
    
    # Execute the problematic call
    print(f"\n⚡ Executing Problematic Tool Call...")
    response = executor.execute_tool(problematic_call)
    
    print(f"   - Success: {response.success}")
    print(f"   - Execution Time: {response.execution_time:.3f}s")
    
    if response.success:
        print(f"   - Result: {response.result}")
        print(f"   - ✅ SUCCESS: Tool executed despite parameter name mismatch")
    else:
        print(f"   - Error: {response.error}")
        print(f"   - ❌ FAILURE: Parameter name mismatch caused execution failure")
    
    # Test the correct case: model returns 'query' parameter  
    print(f"\n🧪 Testing Correct Parameter Mapping...")
    
    correct_call = ToolCall(
        function={
            "name": "wikipedia-api", 
            "arguments": {"query": "Generative AI"}  # CORRECT parameter name
        }
    )
    
    print(f"📤 Correct Tool Call:")
    print(f"   - Function: {correct_call.function_name}")
    print(f"   - Arguments: {correct_call.function_arguments}")
    
    # Execute the correct call
    print(f"\n⚡ Executing Correct Tool Call...")
    response2 = executor.execute_tool(correct_call)
    
    print(f"   - Success: {response2.success}")
    print(f"   - Execution Time: {response2.execution_time:.3f}s")
    
    if response2.success:
        print(f"   - Result Type: {type(response2.result)}")
        result_preview = str(response2.result)[:200] + "..." if len(str(response2.result)) > 200 else str(response2.result)
        print(f"   - Result Preview: {result_preview}")
        print(f"   - ✅ SUCCESS: Tool executed with correct parameter name")
    else:
        print(f"   - Error: {response2.error}")
        print(f"   - ❌ FAILURE: Even correct parameter name failed")
    
    # Test parameter name mapping from input to query
    print(f"\n🔧 Testing Parameter Name Mapping Solution...")
    
    # Manually map 'input' to 'query' before execution
    mapped_arguments = problematic_call.function_arguments.copy()
    if 'input' in mapped_arguments and 'query' not in mapped_arguments:
        mapped_arguments['query'] = mapped_arguments.pop('input')
        print(f"   - Mapped 'input' -> 'query': {mapped_arguments}")
        
        mapped_call = ToolCall(
            function={
                "name": "wikipedia-api",
                "arguments": mapped_arguments
            }
        )
        
        # Execute the mapped call
        print(f"\n⚡ Executing Mapped Tool Call...")
        response3 = executor.execute_tool(mapped_call)
        
        print(f"   - Success: {response3.success}")
        print(f"   - Execution Time: {response3.execution_time:.3f}s")
        
        if response3.success:
            result_preview = str(response3.result)[:200] + "..." if len(str(response3.result)) > 200 else str(response3.result)
            print(f"   - Result Preview: {result_preview}")
            print(f"   - ✅ SUCCESS: Parameter mapping fixed the issue")
        else:
            print(f"   - Error: {response3.error}")
            print(f"   - ❌ FAILURE: Parameter mapping didn't fix the issue")
    
    # Test validation behavior
    print(f"\n🔍 Testing Parameter Validation...")
    
    try:
        from tool_schemas import validate_tool_arguments
        validation_result = validate_tool_arguments(wiki_def, problematic_call.function_arguments)
        print(f"   - Strict Validation: PASSED")
        print(f"   - Validated Args: {validation_result}")
    except Exception as validation_error:
        print(f"   - Strict Validation: FAILED - {validation_error}")
        print(f"   - This explains why the tool execution fails")
    
    # Summary and diagnosis
    print(f"\n📊 DIAGNOSIS SUMMARY")
    print("=" * 60)
    
    issue_identified = not response.success and response2.success
    parameter_mapping_works = 'response3' in locals() and response3.success
    
    print(f"✅ Issue Identified: {'SUCCESS' if issue_identified else 'INCONCLUSIVE'}")
    print(f"✅ Parameter Mapping Solution: {'SUCCESS' if parameter_mapping_works else 'FAILED'}")
    
    if issue_identified:
        print(f"\n🔧 ROOT CAUSE IDENTIFIED:")
        print(f"   - Function definition expects parameter name: 'query'")
        print(f"   - Model/n8n returns parameter name: 'input'")
        print(f"   - Parameter name mismatch causes execution failure")
        print(f"   - Solution: Map 'input' -> 'query' during argument processing")
    
    return issue_identified and parameter_mapping_works

def test_all_builtin_parameter_issues():
    """Test all built-in functions for potential parameter mapping issues."""
    
    print(f"\n🔍 Testing All Built-in Functions for Parameter Issues")
    print("=" * 60)
    
    config = ToolCallingConfig()
    executor = ToolExecutor(config)
    
    # Common parameter name variations that models might use
    common_variations = {
        'query': ['input', 'search', 'term', 'text'],
        'location': ['place', 'city', 'address'],
        'expression': ['formula', 'equation', 'calc'],
        'filename': ['file', 'path', 'name'],
        'content': ['text', 'data', 'body'],
        'to': ['email', 'recipient', 'address'],
        'subject': ['title', 'header'],
        'body': ['content', 'message', 'text']
    }
    
    builtin_functions = [
        'calculate', 'get_current_time', 'get_weather', 'search_web',
        'wikipedia-api', 'wikipedia_api', 'Wikipedia_API',
        'send_email', 'create_file', 'read_file'
    ]
    
    issues_found = []
    
    for func_name in builtin_functions:
        func_def = executor.registry.get_definition(func_name)
        if not func_def:
            continue
            
        print(f"\n📝 Testing Function: {func_name}")
        
        for param_name, param_schema in func_def.parameters.properties.items():
            required = param_name in (func_def.parameters.required or [])
            print(f"   - Parameter: {param_name} ({'required' if required else 'optional'})")
            
            # Check if this parameter has common variations
            if param_name in common_variations:
                variations = common_variations[param_name]
                print(f"   - Common variations: {variations}")
                
                # Test each variation
                for variation in variations:
                    test_args = {variation: "test_value"}
                    
                    test_call = ToolCall(
                        function={
                            "name": func_name,
                            "arguments": test_args
                        }
                    )
                    
                    response = executor.execute_tool(test_call)
                    if not response.success and "missing" in response.error.lower():
                        issues_found.append({
                            'function': func_name,
                            'expected_param': param_name,
                            'provided_param': variation,
                            'error': response.error
                        })
                        print(f"     - ❌ {variation} -> {param_name}: {response.error}")
                    else:
                        print(f"     - ✅ {variation} -> handled correctly")
    
    print(f"\n📊 PARAMETER MAPPING ISSUES SUMMARY")
    print("=" * 60)
    print(f"Issues Found: {len(issues_found)}")
    
    for issue in issues_found:
        print(f"   - {issue['function']}: {issue['provided_param']} -> {issue['expected_param']}")
        print(f"     Error: {issue['error']}")
    
    return issues_found

if __name__ == "__main__":
    print("🚀 Starting Wikipedia Parameter Mapping Tests")
    print("=" * 60)
    
    # Test the specific wikipedia issue
    success = test_wikipedia_parameter_mapping_issue()
    
    # Test all built-in functions for similar issues
    issues = test_all_builtin_parameter_issues()
    
    print(f"\n{'='*60}")
    if success:
        print("✅ Wikipedia parameter mapping issue reproduced and solution validated!")
    else:
        print("❌ Could not reproduce or solve the wikipedia parameter mapping issue")
    
    if issues:
        print(f"⚠️  Found {len(issues)} parameter mapping issues across built-in functions")
    else:
        print("✅ No parameter mapping issues found in built-in functions")
    
    exit(0 if success and not issues else 1)
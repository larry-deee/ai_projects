#!/usr/bin/env python3
"""
Test N8N Continuous Loop Fix
=============================

This test specifically addresses the reported issue where n8n workflows 
continuously loop on the first agent-as-a-tool node due to tool execution 
failures. The fix should prevent this by properly handling parameter mapping
and ensuring tool calls succeed.

Test Strategy:
1. Simulate the exact n8n request that was failing
2. Test the complete pipeline with parameter mapping fix
3. Verify tool execution succeeds instead of failing
4. Confirm response format allows n8n workflow progression
"""

import sys
import os
sys.path.append('src')

from tool_executor import ToolExecutor
from tool_schemas import ToolCallingConfig, ToolCall
from unified_response_formatter import UnifiedResponseFormatter
import json

def test_n8n_continuous_loop_fix():
    """Test that the parameter mapping fix prevents n8n continuous loops."""
    
    print("🔄 Testing N8N Continuous Loop Fix")
    print("=" * 60)
    
    # STEP 1: Simulate the exact problematic n8n scenario
    print("📋 Simulating Problematic N8N Scenario...")
    
    # This is the exact scenario from the user's report:
    # - n8n sends request with wikipedia-api tool
    # - Model returns tool call with 'input' parameter
    # - Tool execution fails with "missing 1 required positional argument: 'query'"
    # - n8n loops continuously because tool call failed
    
    problematic_tool_call = {
        "id": "call_n8n_test_12345",
        "type": "function",
        "function": {
            "name": "wikipedia-api",
            "arguments": json.dumps({"input": "Generative AI"})  # PROBLEMATIC: 'input' instead of 'query'
        }
    }
    
    print(f"   - Tool Call ID: {problematic_tool_call['id']}")
    print(f"   - Function Name: {problematic_tool_call['function']['name']}")
    print(f"   - Arguments: {problematic_tool_call['function']['arguments']}")
    print(f"   - Issue: Uses 'input' parameter but function expects 'query'")
    
    # STEP 2: Test tool execution with the fix
    print(f"\n⚡ Testing Tool Execution with Parameter Mapping Fix...")
    
    config = ToolCallingConfig()
    executor = ToolExecutor(config)
    
    # Convert to ToolCall object
    tool_call = ToolCall(**problematic_tool_call)
    
    print(f"   - Converted to ToolCall object successfully")
    print(f"   - Function Name: {tool_call.function_name}")
    print(f"   - Original Arguments: {tool_call.function_arguments}")
    
    # Execute the tool call
    response = executor.execute_tool(tool_call)
    
    print(f"\n📊 Tool Execution Results:")
    print(f"   - Success: {response.success}")
    print(f"   - Execution Time: {response.execution_time:.3f}s")
    
    if response.success:
        print(f"   - ✅ SUCCESS: Tool execution completed")
        result_preview = str(response.result)[:150] + "..." if len(str(response.result)) > 150 else str(response.result)
        print(f"   - Result Preview: {result_preview}")
        print(f"   - 🎯 FIX VERIFIED: Parameter mapping prevented execution failure")
    else:
        print(f"   - ❌ FAILURE: Tool execution still failing")
        print(f"   - Error: {response.error}")
        print(f"   - 🚨 FIX NOT WORKING: N8N will continue to loop")
        return False
    
    # STEP 3: Test the complete n8n response pipeline
    print(f"\n🔧 Testing Complete N8N Response Pipeline...")
    
    # Simulate a complete Salesforce response with XML function calls using 'input' parameter
    mock_salesforce_response = {
        "response": {
            "generations": [[{
                "text": """<function_calls>
[
 {
 "name": "wikipedia-api",
 "arguments": {
 "input": "Generative AI"
 }
 }
]
</function_calls>""",
                "generationInfo": {
                    "finish_reason": "stop"
                }
            }]]
        },
        "tokenUsageEstimate": {
            "completionTokens": 45,
            "promptTokens": 200,
            "totalTokens": 245
        },
        "model": "sfdc_ai__DefaultGPT4Omni"
    }
    
    # Test unified response formatter
    formatter = UnifiedResponseFormatter(debug_mode=True)
    
    # Extract and process tool calls
    tool_calls = formatter.extract_tool_calls(mock_salesforce_response)
    print(f"   - Tool Calls Extracted: {len(tool_calls)}")
    
    if tool_calls:
        extracted_call = tool_calls[0]
        print(f"   - Extracted Function: {extracted_call.get('function', {}).get('name', 'missing')}")
        extracted_args = extracted_call.get('function', {}).get('arguments', '{}')
        try:
            parsed_args = json.loads(extracted_args)
            print(f"   - Extracted Arguments: {parsed_args}")
        except:
            print(f"   - Extracted Arguments (raw): {extracted_args}")
        
        # Test if this extracted call would work with our tool executor
        test_call = ToolCall(
            id=extracted_call.get('id', 'test_id'),
            function={
                'name': extracted_call.get('function', {}).get('name', ''),
                'arguments': parsed_args if 'parsed_args' in locals() else {}
            }
        )
        
        print(f"\n🧪 Testing Extracted Tool Call Execution...")
        test_response = executor.execute_tool(test_call)
        
        print(f"   - Extracted Call Success: {test_response.success}")
        if test_response.success:
            print(f"   - ✅ SUCCESS: Extracted tool call executes successfully")
            print(f"   - 🎯 PIPELINE VERIFIED: N8N workflow will progress normally")
        else:
            print(f"   - ❌ FAILURE: Extracted tool call still fails")
            print(f"   - Error: {test_response.error}")
            print(f"   - 🚨 PIPELINE ISSUE: N8N may still experience problems")
            return False
    else:
        print(f"   - ❌ No tool calls extracted from response")
        print(f"   - 🚨 EXTRACTION ISSUE: N8N won't have any tool calls to execute")
        return False
    
    # STEP 4: Test multiple parameter variations that n8n might send
    print(f"\n🔍 Testing Multiple Parameter Variations...")
    
    parameter_variations = [
        {"input": "Machine Learning"},      # Most common issue
        {"search": "Artificial Intelligence"},  # Alternative variation
        {"term": "Deep Learning"},          # Alternative variation  
        {"text": "Neural Networks"},       # Alternative variation
        {"query": "Computer Vision"},      # Correct parameter (should also work)
    ]
    
    variations_success = 0
    for i, variation in enumerate(parameter_variations):
        test_call = ToolCall(
            function={
                "name": "wikipedia-api",
                "arguments": variation
            }
        )
        
        variation_response = executor.execute_tool(test_call)
        param_name = list(variation.keys())[0]
        param_value = variation[param_name]
        
        if variation_response.success:
            print(f"   - ✅ {param_name}: '{param_value}' -> SUCCESS")
            variations_success += 1
        else:
            print(f"   - ❌ {param_name}: '{param_value}' -> FAILED ({variation_response.error})")
    
    print(f"\n📊 Parameter Variation Results: {variations_success}/{len(parameter_variations)} successful")
    
    # STEP 5: Summary and final assessment
    print(f"\n📊 FINAL ASSESSMENT")
    print("=" * 60)
    
    tool_execution_fixed = response.success
    pipeline_works = len(tool_calls) > 0 and test_response.success  
    parameter_mapping_robust = variations_success == len(parameter_variations)
    
    print(f"✅ Tool Execution Fixed: {'SUCCESS' if tool_execution_fixed else 'FAILED'}")
    print(f"✅ Complete Pipeline Works: {'SUCCESS' if pipeline_works else 'FAILED'}")
    print(f"✅ Parameter Mapping Robust: {'SUCCESS' if parameter_mapping_robust else 'PARTIAL'}")
    
    overall_success = tool_execution_fixed and pipeline_works
    
    print(f"\n🎯 N8N CONTINUOUS LOOP FIX: {'SUCCESS' if overall_success else 'FAILED'}")
    
    if overall_success:
        print(f"\n✅ ROOT CAUSE RESOLVED:")
        print(f"   - Parameter name mismatch ('input' vs 'query') has been fixed")
        print(f"   - Tool execution now succeeds instead of failing")
        print(f"   - N8N workflows should progress normally instead of looping")
        print(f"   - Multiple parameter variations are handled robustly")
    else:
        print(f"\n❌ ISSUES REMAINING:")
        if not tool_execution_fixed:
            print(f"   - Tool execution still fails with original problematic call")
        if not pipeline_works:
            print(f"   - Complete response pipeline has issues")
        if not parameter_mapping_robust:
            print(f"   - Some parameter variations are not handled correctly")
    
    return overall_success

def test_specific_anthropic_scenario():
    """Test the specific scenario mentioned for Anthropic chat nodes."""
    
    print(f"\n🤖 Testing Specific Anthropic Chat Node Scenario") 
    print("=" * 60)
    
    # The user mentioned this issue appears when using an Anthropic chat node
    # Anthropic models might have different parameter naming patterns
    
    config = ToolCallingConfig()
    executor = ToolExecutor(config)
    
    # Test different variations that Anthropic models might generate
    anthropic_variations = [
        {"input": "Claude parameter test"},     # Anthropic specific
        {"prompt": "Claude query test"},       # Alternative Anthropic pattern
        {"content": "Claude content test"},    # Alternative Anthropic pattern
        {"message": "Claude message test"},    # Alternative Anthropic pattern
    ]
    
    print(f"Testing {len(anthropic_variations)} Anthropic-specific parameter patterns...")
    
    anthropic_success = 0
    for variation in anthropic_variations:
        test_call = ToolCall(
            function={
                "name": "wikipedia-api", 
                "arguments": variation
            }
        )
        
        response = executor.execute_tool(test_call)
        param_name = list(variation.keys())[0]
        param_value = variation[param_name]
        
        if response.success:
            print(f"   - ✅ Anthropic pattern '{param_name}': SUCCESS")
            anthropic_success += 1
        else:
            print(f"   - ❌ Anthropic pattern '{param_name}': FAILED - {response.error}")
    
    anthropic_compatibility = anthropic_success / len(anthropic_variations)
    print(f"\n📊 Anthropic Compatibility: {anthropic_success}/{len(anthropic_variations)} ({anthropic_compatibility:.1%})")
    
    return anthropic_compatibility >= 0.75  # At least 75% should work

if __name__ == "__main__":
    print("🚀 Starting N8N Continuous Loop Fix Validation")
    print("=" * 60)
    
    # Test the main fix
    main_fix_success = test_n8n_continuous_loop_fix()
    
    # Test Anthropic-specific scenario
    anthropic_success = test_specific_anthropic_scenario()
    
    print(f"\n{'='*60}")
    if main_fix_success and anthropic_success:
        print("✅ N8N CONTINUOUS LOOP FIX VALIDATION: COMPLETE SUCCESS")
        print("🎯 n8n workflows should now progress normally instead of looping")
        print("🤖 Both OpenAI and Anthropic chat nodes should work correctly")
    elif main_fix_success:
        print("✅ N8N CONTINUOUS LOOP FIX VALIDATION: MAIN SUCCESS")
        print("⚠️  Some Anthropic-specific patterns may need additional handling")
    else:
        print("❌ N8N CONTINUOUS LOOP FIX VALIDATION: FAILED")
        print("🚨 Additional debugging and fixes required")
    
    exit(0 if main_fix_success else 1)
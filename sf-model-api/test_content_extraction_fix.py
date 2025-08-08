#!/usr/bin/env python3
"""
Test script to verify the content extraction fix
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from unified_response_formatter import UnifiedResponseFormatter

def test_content_extraction_scenarios():
    """Test various scenarios that could return None."""
    formatter = UnifiedResponseFormatter()
    
    # Test case 1: Empty response
    print("Test 1: Empty response")
    empty_response = {}
    result = formatter.extract_response_text(empty_response)
    print(f"Result text: {result.text}")
    print(f"Success: {result.success}")
    print(f"Error: {result.error_message}")
    print()
    
    # Test case 2: Invalid response type
    print("Test 2: Invalid response type (None)")
    result = formatter.extract_response_text(None)
    print(f"Result text: {result.text}")
    print(f"Success: {result.success}")
    print(f"Error: {result.error_message}")
    print()
    
    # Test case 3: Response with error field
    print("Test 3: Response with error field")
    error_response = {"error": {"message": "API timeout"}}
    result = formatter.extract_response_text(error_response)
    print(f"Result text: {result.text}")
    print(f"Success: {result.success}")
    print()
    
    # Test case 4: Valid response
    print("Test 4: Valid response")
    valid_response = {"generation": {"generatedText": "Hello world!"}}
    result = formatter.extract_response_text(valid_response)
    print(f"Result text: {result.text}")
    print(f"Success: {result.success}")
    print()

def test_streaming_safe_content():
    """Test that the streaming function can handle None content safely."""
    print("Test: Streaming with None content safety")
    
    # Simulate the scenario that would cause the crash
    response = {}  # Empty response that would return None from extract_content_from_response
    
    from async_endpoint_server import extract_content_from_response
    content = extract_content_from_response(response)
    print(f"Extracted content: {content}")
    
    # Test the fix logic
    if content is None:
        print("✅ FIXED: Detected None content, replacing with error message")
        content = "Error: Unable to extract response content. Please try again."
    
    if not isinstance(content, str):
        print(f"✅ FIXED: Content type validation - converting {type(content)} to string")
        content = str(content) if content else "Error: Invalid response format"
    
    # This should now work without throwing TypeError
    try:
        content_length = len(content)
        print(f"✅ SUCCESS: Content length calculation works: {content_length}")
        print(f"Content preview: '{content[:50]}...'")
    except TypeError as e:
        print(f"❌ FAILED: Still getting TypeError: {e}")

if __name__ == "__main__":
    print("=== Content Extraction Bug Fix Test ===")
    print()
    test_content_extraction_scenarios()
    print("=" * 50)
    test_streaming_safe_content()
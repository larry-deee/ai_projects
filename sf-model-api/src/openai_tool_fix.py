#!/usr/bin/env python3
"""
OpenAI Tool-Call Repair Shim
============================

Universal tool-call repair system that fixes "Tool call missing function name" errors
and ensures all tool_calls comply with OpenAI v1 specification format.

Key Features:
- Fixes missing function.name fields permanently
- Ensures JSON-string arguments format compliance  
- Handles malformed tool calls gracefully
- Provides fallback for edge cases
- Thread-safe operations

Usage:
    from openai_tool_fix import repair_openai_tool_calls
    
    message, was_repaired = repair_openai_tool_calls(message, tools)
    if was_repaired:
        logger.debug("🔧 Tool calls repaired for OpenAI compliance")

Architecture Integration:
- Integrates seamlessly with existing response pipeline
- Works with all backends (Anthropic, Gemini, OpenAI-native)
- Preserves original tool functionality while fixing format issues
- Performance optimized with early returns and minimal processing
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Compiled regex for performance - removes non-alphanumeric characters for slugs
ALLOWED = re.compile(r"[^A-Za-z0-9_-]")

def _slug(s: str) -> str:
    """
    Convert string to safe slug format for function names.
    
    Args:
        s: Input string to slugify
        
    Returns:
        str: Safe slug limited to 64 characters
    """
    return ALLOWED.sub("_", str(s))[:64]

def _json_str(v: Union[str, Dict, Any]) -> str:
    """
    Ensure arguments are in JSON string format as required by OpenAI spec.
    
    Args:
        v: Arguments value that needs to be JSON string
        
    Returns:
        str: Valid JSON string representation
    """
    if isinstance(v, str):
        try:
            # If it's already valid JSON, return as-is
            json.loads(v)
            return v
        except Exception:
            # If it's a string but not valid JSON, wrap it in JSON
            return json.dumps(v, ensure_ascii=False)
    
    # For all other types, convert to JSON string
    return json.dumps(v or {}, separators=(',', ':'), ensure_ascii=False)

def repair_openai_tool_calls(message: Dict[str, Any], tools: Optional[List[Dict[str, Any]]]) -> Tuple[Dict[str, Any], bool]:
    """
    Repair tool calls in OpenAI message to ensure v1 specification compliance.
    
    This function fixes common issues with tool_calls that cause "Tool call missing function name"
    errors and other OpenAI compatibility problems:
    
    1. Missing function.name fields - Uses tool definitions, fallback names, or context
    2. Non-string arguments - Converts to required JSON string format
    3. Malformed tool call structure - Rebuilds with proper OpenAI format
    4. Missing required fields - Adds defaults (id, type) as needed
    
    Args:
        message: OpenAI message dict that may contain tool_calls
        tools: Optional tool definitions for name resolution
        
    Returns:
        Tuple[Dict[str, Any], bool]: (repaired_message, was_changed)
            - repaired_message: Message with fixed tool_calls
            - was_changed: True if repairs were made
    """
    tool_calls = message.get("tool_calls")
    if not tool_calls:
        return message, False
    
    # Extract single tool name if only one tool is available (common pattern)
    only_tool_name = None
    if tools and len(tools) == 1:
        function_def = (tools[0].get("function") or {})
        only_tool_name = function_def.get("name")
    
    fixed_calls = []
    changed = False
    
    for idx, tool_call in enumerate(tool_calls, 1):
        if not isinstance(tool_call, dict):
            # Skip invalid tool calls that aren't dictionaries
            logger.warning(f"🔧 Skipping invalid tool call (not dict): {type(tool_call)}")
            changed = True
            continue
        
        # Extract function info from various possible locations
        function_info = tool_call.get("function") or {}
        
        # Try to find function name from multiple sources
        function_name = (
            function_info.get("name") or           # Standard location
            tool_call.get("name") or               # Alternative location
            tool_call.get("tool_name") or          # Some APIs use this
            tool_call.get("function_name") or      # Another variation
            only_tool_name                         # Fallback to single tool name
        )
        
        # Extract arguments from various possible locations
        arguments = (
            function_info.get("arguments") or      # Standard location
            tool_call.get("arguments") or          # Alternative location
            tool_call.get("input") or              # Anthropic style
            tool_call.get("params") or             # Generic parameter name
            {}                                     # Final fallback
        )
        
        # If we still can't find a function name, we cannot recover this tool call
        if not function_name:
            logger.warning(f"🔧 Cannot recover tool call - missing function name in all locations: {tool_call}")
            changed = True
            continue
        
        # Build properly formatted OpenAI tool call
        repaired_call = {
            "id": tool_call.get("id") or f"call_{idx}_{int(hash(str(tool_call))) % 10000}",
            "type": "function",
            "function": {
                "name": _slug(function_name),
                "arguments": _json_str(arguments)
            }
        }
        
        # Check if this call needed repair
        if repaired_call != tool_call:
            changed = True
            logger.debug(f"🔧 Repaired tool call: {function_name}")
        
        fixed_calls.append(repaired_call)
    
    # Update message if we have valid fixed calls
    if fixed_calls:
        message = message.copy()  # Don't mutate original
        message["tool_calls"] = fixed_calls
        # Ensure content is never null (OpenAI requirement)
        if message.get("content") is None:
            message["content"] = ""
        return message, changed
    
    # If no calls could be recovered, remove tool_calls entirely
    if changed:  # We had tool_calls but couldn't recover any
        message = message.copy()
        message.pop("tool_calls", None)
        # Ensure content exists when tool_calls are removed
        if not message.get("content"):
            message["content"] = "Tool calls were present but could not be processed due to formatting issues."
        logger.warning("🔧 All tool calls removed due to irrecoverable formatting issues")
        
    return message, changed

def repair_openai_response(response: Dict[str, Any], tools: Optional[List[Dict[str, Any]]] = None) -> Tuple[Dict[str, Any], bool]:
    """
    Repair an entire OpenAI response by fixing all tool_calls in all choices.
    
    Args:
        response: Full OpenAI response dict
        tools: Optional tool definitions for repair context
        
    Returns:
        Tuple[Dict[str, Any], bool]: (repaired_response, any_changes_made)
    """
    if not isinstance(response, dict) or "choices" not in response:
        return response, False
    
    choices = response.get("choices", [])
    if not choices:
        return response, False
    
    response = response.copy()  # Don't mutate original
    any_changed = False
    
    for i, choice in enumerate(choices):
        if not isinstance(choice, dict) or "message" not in choice:
            continue
            
        message = choice["message"]
        if not isinstance(message, dict):
            continue
        
        repaired_message, was_changed = repair_openai_tool_calls(message, tools)
        
        if was_changed:
            # Update the choice with repaired message
            response["choices"][i] = choice.copy()
            response["choices"][i]["message"] = repaired_message
            
            # Update finish_reason if tool calls are present
            if repaired_message.get("tool_calls"):
                response["choices"][i]["finish_reason"] = "tool_calls"
            
            any_changed = True
    
    return response, any_changed

def validate_tool_calls_format(tool_calls: List[Dict[str, Any]]) -> List[str]:
    """
    Validate tool calls format and return list of issues found.
    
    Args:
        tool_calls: List of tool call dictionaries to validate
        
    Returns:
        List[str]: List of validation error messages (empty if valid)
    """
    if not isinstance(tool_calls, list):
        return ["tool_calls must be a list"]
    
    issues = []
    
    for i, call in enumerate(tool_calls):
        if not isinstance(call, dict):
            issues.append(f"tool_calls[{i}]: must be a dictionary")
            continue
        
        # Check required fields
        if "id" not in call:
            issues.append(f"tool_calls[{i}]: missing required 'id' field")
        
        if call.get("type") != "function":
            issues.append(f"tool_calls[{i}]: 'type' must be 'function'")
        
        function_info = call.get("function")
        if not isinstance(function_info, dict):
            issues.append(f"tool_calls[{i}]: 'function' must be a dictionary")
            continue
        
        if not function_info.get("name"):
            issues.append(f"tool_calls[{i}]: function.name is missing or empty")
        
        arguments = function_info.get("arguments")
        if arguments is not None:
            if not isinstance(arguments, str):
                issues.append(f"tool_calls[{i}]: function.arguments must be a JSON string")
            else:
                try:
                    json.loads(arguments)
                except json.JSONDecodeError:
                    issues.append(f"tool_calls[{i}]: function.arguments is not valid JSON")
    
    return issues

# Convenience functions for common use cases
def ensure_tool_calls_compliance(message: Dict[str, Any], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Ensure message tool_calls are OpenAI compliant (convenience function).
    
    Args:
        message: Message to check/repair
        tools: Optional tool definitions
        
    Returns:
        Dict[str, Any]: Message with compliant tool_calls
    """
    repaired_message, _ = repair_openai_tool_calls(message, tools)
    return repaired_message

def check_tool_calls_health(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check the health of tool_calls in a response (diagnostic function).
    
    Args:
        response: OpenAI response to analyze
        
    Returns:
        Dict[str, Any]: Health report with statistics and issues
    """
    if not isinstance(response, dict) or "choices" not in response:
        return {"status": "no_choices", "tool_calls_found": 0}
    
    total_calls = 0
    total_issues = 0
    choices_with_tools = 0
    all_issues = []
    
    for i, choice in enumerate(response.get("choices", [])):
        message = choice.get("message", {})
        tool_calls = message.get("tool_calls", [])
        
        if tool_calls:
            choices_with_tools += 1
            total_calls += len(tool_calls)
            
            issues = validate_tool_calls_format(tool_calls)
            total_issues += len(issues)
            all_issues.extend([f"choice[{i}] {issue}" for issue in issues])
    
    return {
        "status": "healthy" if total_issues == 0 else "issues_found",
        "total_choices": len(response.get("choices", [])),
        "choices_with_tool_calls": choices_with_tools,
        "total_tool_calls": total_calls,
        "total_issues": total_issues,
        "issues": all_issues[:10],  # Limit to first 10 issues for readability
        "truncated": len(all_issues) > 10
    }

# Export main functions
__all__ = [
    "repair_openai_tool_calls",
    "repair_openai_response", 
    "validate_tool_calls_format",
    "ensure_tool_calls_compliance",
    "check_tool_calls_health"
]
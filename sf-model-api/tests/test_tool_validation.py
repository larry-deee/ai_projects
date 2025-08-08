#!/usr/bin/env python3
"""
Tool Validation Test Suite
==========================

Tests for the enhanced tool definition validation to ensure 100% OpenAI 
and Anthropic API specification compliance.
"""

import json
import pytest
import sys
import os
from unittest.mock import Mock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tool_schemas import (
    validate_tool_definitions,
    validate_anthropic_tool_definitions,
    convert_openai_to_anthropic_tools,
    validate_tools_with_format,
    detect_tool_format,
    ToolCallingValidationError,
    create_tool_validation_error_response,
    parse_tool_error_response
)


class TestOpenAIToolValidation:
    """Test cases for OpenAI tool definition validation."""
    
    def test_valid_openai_tool(self):
        """Test that valid OpenAI tools pass validation."""
        valid_tool = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
        
        result = validate_tool_definitions([valid_tool])
        assert len(result) == 1
        assert result[0].function.name == "get_weather"
    
    def test_missing_type_field(self):
        """Test that tools missing 'type' field are rejected."""
        invalid_tool = {
            "function": {
                "name": "test_func",
                "description": "Test function"
            }
        }
        
        with pytest.raises(ToolCallingValidationError) as excinfo:
            validate_tool_definitions([invalid_tool])
        
        assert "missing required field: 'type'" in str(excinfo.value)
    
    def test_invalid_type_value(self):
        """Test that tools with invalid 'type' value are rejected."""
        invalid_tool = {
            "type": "invalid",
            "function": {
                "name": "test_func",
                "description": "Test function"
            }
        }
        
        with pytest.raises(ToolCallingValidationError) as excinfo:
            validate_tool_definitions([invalid_tool])
        
        assert "invalid 'type': 'invalid'. Must be 'function'" in str(excinfo.value)
    
    def test_missing_function_field(self):
        """Test that tools missing 'function' field are rejected."""
        invalid_tool = {
            "type": "function"
        }
        
        with pytest.raises(ToolCallingValidationError) as excinfo:
            validate_tool_definitions([invalid_tool])
        
        assert "missing required field: 'function'" in str(excinfo.value)
    
    def test_missing_function_name(self):
        """Test that functions missing 'name' field are rejected."""
        invalid_tool = {
            "type": "function",
            "function": {
                "description": "Test function"
            }
        }
        
        with pytest.raises(ToolCallingValidationError) as excinfo:
            validate_tool_definitions([invalid_tool])
        
        assert "missing required fields: name" in str(excinfo.value)
    
    def test_invalid_parameters_type(self):
        """Test that parameters with invalid 'type' are rejected."""
        invalid_tool = {
            "type": "function",
            "function": {
                "name": "test_func",
                "description": "Test function",
                "parameters": {
                    "type": "invalid_type",
                    "properties": {}
                }
            }
        }
        
        with pytest.raises(ToolCallingValidationError) as excinfo:
            validate_tool_definitions([invalid_tool])
        
        assert "parameters 'type' must be 'object'" in str(excinfo.value)
    
    def test_invalid_property_type(self):
        """Test that properties with invalid types are rejected."""
        invalid_tool = {
            "type": "function",
            "function": {
                "name": "test_func",
                "description": "Test function",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {
                            "type": "invalid_property_type",
                            "description": "Test parameter"
                        }
                    }
                }
            }
        }
        
        with pytest.raises(ToolCallingValidationError) as excinfo:
            validate_tool_definitions([invalid_tool])
        
        assert "has invalid type: 'invalid_property_type'" in str(excinfo.value)
    
    def test_array_property_missing_items(self):
        """Test that array properties without 'items' are rejected."""
        invalid_tool = {
            "type": "function",
            "function": {
                "name": "test_func",
                "description": "Test function",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "array_param": {
                            "type": "array",
                            "description": "Array parameter"
                        }
                    }
                }
            }
        }
        
        with pytest.raises(ToolCallingValidationError) as excinfo:
            validate_tool_definitions([invalid_tool])
        
        assert "must specify 'items' schema" in str(excinfo.value)
    
    def test_required_property_not_in_properties(self):
        """Test that required properties must exist in properties."""
        invalid_tool = {
            "type": "function",
            "function": {
                "name": "test_func",
                "description": "Test function",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {
                            "type": "string",
                            "description": "Parameter 1"
                        }
                    },
                    "required": ["param1", "param2"]  # param2 doesn't exist
                }
            }
        }
        
        with pytest.raises(ToolCallingValidationError) as excinfo:
            validate_tool_definitions([invalid_tool])
        
        assert "has required properties that don't exist: param2" in str(excinfo.value)


class TestAnthropicToolValidation:
    """Test cases for Anthropic tool definition validation."""
    
    def test_valid_anthropic_tool(self):
        """Test that valid Anthropic tools pass validation."""
        valid_tool = {
            "name": "get_weather",
            "description": "Get weather for a location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["location"]
            }
        }
        
        result = validate_anthropic_tool_definitions([valid_tool])
        assert len(result) == 1
        assert result[0]["name"] == "get_weather"
    
    def test_anthropic_missing_required_fields(self):
        """Test that Anthropic tools missing required fields are rejected."""
        invalid_tool = {
            "name": "test_func",
            # Missing description and input_schema
        }
        
        with pytest.raises(ToolCallingValidationError) as excinfo:
            validate_anthropic_tool_definitions([invalid_tool])
        
        assert "missing required fields: description, input_schema" in str(excinfo.value)
    
    def test_anthropic_invalid_input_schema_type(self):
        """Test that Anthropic tools with invalid input_schema type are rejected."""
        invalid_tool = {
            "name": "test_func",
            "description": "Test function",
            "input_schema": {
                "type": "invalid",
                "properties": {}
            }
        }
        
        with pytest.raises(ToolCallingValidationError) as excinfo:
            validate_anthropic_tool_definitions([invalid_tool])
        
        assert "input_schema 'type' must be 'object'" in str(excinfo.value)


class TestToolFormatDetection:
    """Test cases for tool format detection and conversion."""
    
    def test_detect_openai_format(self):
        """Test detection of OpenAI format tools."""
        openai_tools = [{
            "type": "function",
            "function": {
                "name": "test_func",
                "description": "Test"
            }
        }]
        
        format_type = detect_tool_format(openai_tools)
        assert format_type == "openai"
    
    def test_detect_anthropic_format(self):
        """Test detection of Anthropic format tools."""
        anthropic_tools = [{
            "name": "test_func",
            "description": "Test",
            "input_schema": {
                "type": "object",
                "properties": {}
            }
        }]
        
        format_type = detect_tool_format(anthropic_tools)
        assert format_type == "anthropic"
    
    def test_convert_openai_to_anthropic(self):
        """Test conversion from OpenAI to Anthropic format."""
        openai_tools = [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"}
                    }
                }
            }
        }]
        
        anthropic_tools = convert_openai_to_anthropic_tools(openai_tools)
        assert len(anthropic_tools) == 1
        assert anthropic_tools[0]["name"] == "get_weather"
        assert "input_schema" in anthropic_tools[0]


class TestErrorHandling:
    """Test cases for error handling and response formatting."""
    
    def test_tool_validation_error_response_format(self):
        """Test that validation errors are formatted correctly."""
        errors = ["Tool 'test' missing required field: 'type'"]
        error_response, status_code = create_tool_validation_error_response(errors)
        
        assert status_code == 400
        assert "error" in error_response
        assert error_response["error"]["type"] == "invalid_request_error"
        assert error_response["error"]["code"] == "tool_validation_error"
    
    def test_parse_tool_error_response(self):
        """Test parsing of various exception types."""
        # Test ToolCallingValidationError
        validation_error = ToolCallingValidationError("Test validation error")
        response, status = parse_tool_error_response(validation_error)
        
        assert status == 400
        assert response["error"]["code"] == "tool_validation_error"
        
        # Test generic ValueError
        value_error = ValueError("Test value error")
        response, status = parse_tool_error_response(value_error)
        
        assert status == 400
        assert response["error"]["code"] == "value_error"


if __name__ == "__main__":
    # Run the test suite
    pytest.main([__file__, "-v"])
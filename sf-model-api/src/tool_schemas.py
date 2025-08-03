#!/usr/bin/env python3
"""
Tool Calling Schemas and Validation
==================================

Pydantic models for OpenAI-compatible tool calling validation.
Provides robust schema validation for function/tool definitions and responses.

Based on OpenAI's function calling specification:
https://platform.openai.com/docs/guides/function-calling
"""

import json
import uuid
import re
from typing import Dict, Any, List, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)


class ContentObject(BaseModel):
    """Content object for OpenAI-compatible array content."""
    type: str = Field("text", description="Type of content")
    text: str = Field(..., description="Text content")

    @validator('type')
    def validate_type(cls, v):
        """Validate content type."""
        allowed_types = ['text', 'image_url', 'image_file']
        if v not in allowed_types:
            logger.warning(f"Unusual content type '{v}', proceeding anyway")
        return v


class FunctionParameterType(str, Enum):
    """Supported function parameter types."""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolChoiceType(str, Enum):
    """Tool choice strategies."""
    AUTO = "auto"
    NONE = "none"
    REQUIRED = "required"


class ParameterSchema(BaseModel):
    """Schema for function parameters."""
    type: FunctionParameterType = Field(..., description="Type of the parameter")
    description: Optional[str] = Field(None, description="Description of the parameter")
    enum: Optional[List[Any]] = Field(None, description="Allowed values for the parameter")
    items: Optional[Dict[str, Any]] = Field(None, description="Schema for array items")
    properties: Optional[Dict[str, Any]] = Field(None, description="Schema for object properties")
    required: Optional[List[str]] = Field(None, description="Required properties for object type")
    default: Any = Field(None, description="Default value for the parameter")
    
    @validator('items')
    def validate_items(cls, v, values):
        """Validate items schema when type is array."""
        if values.get('type') == FunctionParameterType.ARRAY and v is None:
            raise ValueError("items schema is required when type is 'array'")
        return v
    
    @validator('properties')
    def validate_properties(cls, v, values):
        """Validate properties schema when type is object."""
        if values.get('type') == FunctionParameterType.OBJECT and v is None:
            raise ValueError("properties schema is required when type is 'object'")
        return v


class FunctionParameters(BaseModel):
    """Function parameters schema following OpenAI specification."""
    type: str = Field("object", description="Type of parameters, must be 'object'")
    properties: Dict[str, ParameterSchema] = Field(
        default_factory=dict,
        description="Schema for each parameter"
    )
    required: Optional[List[str]] = Field(
        None,
        description="List of required parameter names"
    )
    additionalProperties: Optional[Union[bool, Dict[str, Any]]] = Field(
        None,
        description="Whether additional properties are allowed (boolean) or schema for additional properties (object)"
    )
    schema_version: Optional[str] = Field(
        None,
        description="JSON Schema specification version",
        alias="$schema"
    )
    description: Optional[str] = Field(
        None,
        description="Description of the parameters object"
    )
    
    @validator('type')
    def validate_type(cls, v):
        """Validate type is 'object'."""
        if v != "object":
            raise ValueError("Function parameters type must be 'object'")
        return v


class FunctionDefinition(BaseModel):
    """Function definition schema."""
    name: str = Field(..., description="Name of the function", min_length=1, max_length=64)
    description: Optional[str] = Field(None, description="Description of the function")
    parameters: FunctionParameters = Field(
        default_factory=lambda: FunctionParameters(),
        description="Parameters schema for the function"
    )
    strict: Optional[bool] = Field(
        default=False,
        description="Whether to enforce strict parameter validation"
    )
    
    @validator('name')
    def validate_name(cls, v):
        """Validate function name format according to OpenAI specification."""
        if not v or not isinstance(v, str):
            raise ValueError("Function name must be a non-empty string")
        
        # OpenAI allows: letters, numbers, underscores, and hyphens
        # Maximum length is 64 characters
        if len(v) > 64:
            raise ValueError("Function name must be 64 characters or less")
        
        # Check for valid characters (OpenAI spec: letters, numbers, underscores, hyphens)
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Function name can only contain letters, numbers, underscores, and hyphens")
        
        # Must start with a letter or underscore
        if not (v[0].isalpha() or v[0] == '_'):
            raise ValueError("Function name must start with a letter or underscore")
        
        return v
    
    @validator('parameters')
    def validate_parameters(cls, v):
        """Validate parameters schema with enhanced CLI-style parameter support."""
        for param_name in v.properties.keys():
            # Support both traditional identifiers and CLI-style parameters
            if not is_valid_parameter_name(param_name):
                raise ValueError(f"Parameter name '{param_name}' is not valid. Must be either a valid Python identifier or a CLI-style parameter (e.g., '-B', '--long-name', 'long-name')")
        return v


class ToolType(str, Enum):
    """Tool types."""
    FUNCTION = "function"


class ToolDefinition(BaseModel):
    """Tool definition schema."""
    type: ToolType = Field(default=ToolType.FUNCTION, description="Type of the tool")
    function: FunctionDefinition = Field(..., description="Function definition")


class ToolChoice(BaseModel):
    """Tool choice specification."""
    type: ToolChoiceType = Field(..., description="Type of tool choice")
    function: Optional[Dict[str, str]] = Field(None, description="Specific function to call")
    
    @validator('function')
    def validate_function_choice(cls, v, values):
        """Validate function choice when type is not 'none'."""
        if values.get('type') != ToolChoiceType.NONE and v is not None:
            if 'name' not in v or not v['name']:
                raise ValueError("function must contain 'name' field when specified")
        return v


class ToolCallParameter(BaseModel):
    """Tool call parameter value."""
    value: Any = Field(..., description="Parameter value")


class ToolCall(BaseModel):
    """Tool call schema."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the tool call")
    type: str = Field(default="function", description="Type of the tool call")
    function: Dict[str, Any] = Field(..., description="Function call details")
    
    @validator('function')
    def validate_function(cls, v):
        """Validate function call details."""
        required_fields = ['name', 'arguments']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Function call missing required field: {field}")
        
        # Validate arguments format
        if isinstance(v['arguments'], str):
            try:
                # Try to parse as JSON
                json.loads(v['arguments'])
            except json.JSONDecodeError:
                raise ValueError("Function arguments must be valid JSON string")
        
        return v
    
    @property
    def function_name(self) -> str:
        """Get the function name."""
        return self.function['name']
    
    @property
    def function_arguments(self) -> Dict[str, Any]:
        """Get the function arguments as dictionary."""
        args = self.function['arguments']
        if isinstance(args, str):
            return json.loads(args)
        return args


class ToolMessage(BaseModel):
    """Tool message schema for conversation history."""
    role: Literal["tool"] = Field(default="tool", description="Role of the message")
    tool_call_id: str = Field(..., description="ID of the tool call this message responds to")
    content: str = Field(..., description="Content of the tool message")
    
    @validator('content')
    def validate_content(cls, v):
        """Validate tool message content."""
        if not v.strip():
            raise ValueError("Tool message content cannot be empty")
        return v


class ChatRole(str, Enum):
    """Chat message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolMessageRole(BaseModel):
    """Enhanced message role with tool support and OpenAI-compatible content."""
    role: ChatRole = Field(..., description="Role of the message")
    content: Optional[Union[str, List[ContentObject]]] = Field(None, description="Content of the message (string or array of content objects)")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="Tool calls made by assistant")
    tool_call_id: Optional[str] = Field(None, description="Tool call ID for tool messages")
    
    @validator('content')
    def validate_content(cls, v, values):
        """Validate content format based on role."""
        if v is None:
            # Content can be None for assistant messages with tool_calls
            if values.get('role') == ChatRole.ASSISTANT and values.get('tool_calls'):
                return None
            elif values.get('role') in [ChatRole.USER, ChatRole.TOOL]:
                raise ValueError(f"Content is required for {values.get('role')} role")
            return None
        
        # Handle array content (OpenAI format)
        if isinstance(v, list):
            if not v: # Empty array
                raise ValueError("Content array cannot be empty")
            
            # Validate each content object
            for i, content_obj in enumerate(v):
                if isinstance(content_obj, dict):
                    # Convert dict to Content Object if needed
                    try:
                        v[i] = ContentObject(**content_obj)
                    except Exception as e:
                        raise ValueError(f"Invalid content object at index {i}: {e}")
                elif not isinstance(content_obj, ContentObject):
                    raise ValueError(f"Content array items must be Content Object or dict, got {type(content_obj)}")
        
        # Handle string content (existing format)
        elif isinstance(v, str):
            if values.get('role') == ChatRole.TOOL and not v.strip():
                raise ValueError("Tool message content cannot be empty")
        
        else:
            raise ValueError(f"Content must be string or array of Content Object, got {type(v)}")
        
        return v
    
    @validator('tool_calls')
    def validate_tool_calls(cls, v, values):
        """Validate tool calls based on role."""
        if values.get('role') == ChatRole.ASSISTANT and v is not None:
            if len(v) == 0:
                raise ValueError("tool_calls cannot be empty list for assistant role")
        elif values.get('role') != ChatRole.ASSISTANT and v is not None:
            raise ValueError("tool_calls only allowed for assistant role")
        return v
    
    @validator('tool_call_id')
    def validate_tool_call_id(cls, v, values):
        """Validate tool call ID based on role."""
        if values.get('role') == ChatRole.TOOL and v is None:
            raise ValueError("tool_call_id is required for tool messages")
        elif values.get('role') != ChatRole.TOOL and v is not None:
            raise ValueError("tool_call_id only allowed for tool messages")
        return v
    
    @property
    def content_text(self) -> Optional[str]:
        """Get content as plain text, handling both string and array formats."""
        if self.content is None:
            return None
        
        if isinstance(self.content, str):
            return self.content
        
        if isinstance(self.content, list):
            # Extract text from content objects
            text_parts = []
            for content_obj in self.content:
                if isinstance(content_obj, ContentObject):
                    text_parts.append(content_obj.text)
                elif isinstance(content_obj, dict):
                    # Handle dict format (raw input)
                    if 'text' in content_obj:
                        text_parts.append(content_obj['text'])
            return ''.join(text_parts)
        
        return None
    
    @property
    def content_as_list(self) -> List[ContentObject]:
        """Get content as list of Content Object, converting from string if needed."""
        if self.content is None:
            return []
        
        if isinstance(self.content, list):
            return self.content
        
        if isinstance(self.content, str):
            return [ContentObject(type="text", text=self.content)]
        
        return []


class ToolResponse(BaseModel):
    """Tool response schema."""
    success: bool = Field(..., description="Whether the tool execution was successful")
    result: Any = Field(None, description="Result of the tool execution")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time: float = Field(..., description="Time taken to execute the tool in seconds")


class ToolCallingConfig(BaseModel):
    """Configuration for tool calling behavior."""
    max_concurrent_calls: int = Field(
        default=3,
        description="Maximum number of parallel tool calls",
        ge=1,
        le=10
    )
    timeout: float = Field(
        default=30.0,
        description="Timeout for individual tool execution in seconds",
        ge=1.0,
        le=300.0
    )
    allow_dangerous_functions: bool = Field(
        default=False,
        description="Whether to allow potentially dangerous functions"
    )
    strict_parameter_validation: bool = Field(
        default=True,
        description="Whether to enforce strict parameter validation"
    )
    enable_tool_output_parsing: bool = Field(
        default=True,
        description="Whether to enable intelligent parsing of tool responses"
    )


class ToolCallingPromptTemplate(BaseModel):
    """Template for generating tool calling prompts."""
    system_prompt: str = Field(
        default="You are a helpful assistant with access to tools. "
        "When you need to use a tool, respond with your answer wrapped in "
        "<function_calls> and </function_calls> tags in the following format:\n\n"
        "<function_calls>\n"
        "[\n"
        " {\n"
        " \"name\": \"function_name\",\n"
        " \"arguments\": {\n"
        " \"param1\": \"value1\",\n"
        " \"param2\": \"value2\"\n"
        " }\n"
        " }\n"
        "]\n"
        "</function_calls>\n\n"
        "Only call functions when necessary. If you can answer the question "
        "directly, do so without calling functions.\n\n"
        "⚠️ n8n COMPATIBILITY MODE:\n"
        "When you see parameters marked as 'Parameter value will be determined by the model automatically' "
        "or descriptions containing $fromAI() references, you MUST:\n"
        "1. Analyze the user's message and conversation context thoroughly\n"
        "2. Generate appropriate values for these parameters based on context\n"
        "3. Include these generated values in your function call arguments\n"
        "4. Treat $fromAI() references as context clues, not executable commands\n\n"
        "🔍 AUTOMATIC PARAMETER EXTRACTION RULES:\n"
        "- IDENTIFY: Look for [AUTO_PARAM:...] markers and parameter descriptions\n"
        "- ANALYZE: Extract relevant information from user message and context\n"
        "- INFER: Use semantic understanding to determine appropriate values\n"
        "- VALIDATE: Ensure values match the expected parameter type\n"
        "- GENERATE: Include inferred values in your function call JSON\n\n"
        "📋 CONTEXT ANALYSIS STRATEGY:\n"
        "1. **Direct Extraction**: If user explicitly mentions values (e.g., 'Send to John'), use 'John'\n"
        "2. **Contextual Inference**: If user mentions 'Use API xyz-123', use 'xyz-123'\n"
        "3. **Intent Analysis**: Determine user's goal from conversation history\n"
        "4. **Semantic Matching**: Extract implicit values from related concepts\n"
        "5. **Default Generation**: Use sensible defaults when context is unclear\n\n"
        "💡 EXAMPLES OF AUTOMATIC PARAMETER HANDLING:\n"
        "- User: 'Send email to John about meeting tomorrow + $fromAI('subject')'\n"
        " → Use subject: 'Meeting Tomorrow' (inferred from context)\n"
        "- User: 'Calculate total for items: 15, 27, 33 + $fromAI('operation')'\n"
        " → Use operation: 'sum' (inferred from 'Calculate total')\n"
        "- User: 'Get weather for London but use metric units + $fromAI('units')'\n"
        " → Use units: 'metric' (explicitly mentioned)\n\n"
        "🔧 SALESFORCE MODEL ADVANTAGES:\n"
        "As a Salesforce model (Claude, GPT-4, Gemini), you excel at:\n"
        "- **Semantic Analysis**: Understanding nuanced user intent\n"
        "- **Context Integration**: Processing conversation history holistically\n"
        "- **Inference Generation**: Creating appropriate parameter values\n"
        "- **Coherence Tracking**: Maintaining consistency across messages\n\n"
        "🎯 EXECUTION PRINCIPLE:\n"
        "NEVER respond with 'Please provide the value for X'. ALWAYS determine values from context.",
        description="System prompt for tool calling"
    )
    function_list_template: str = Field(
        default="Available functions:\n{functions}\n\n"
        "When calling functions, provide all required parameters. "
        "Use valid JSON for arguments.\n\n"
        "🔸 IMPORTANT: For parameters marked as 'Parameter value will be determined by the model automatically', "
        "you must generate appropriate values based on the user's message and context.",
        description="Template for listing available functions"
    )
    function_template: str = Field(
        default="Function: {name}\n"
        "Description: {description}\n"
        "Parameters: {parameters}",
        description="Template for individual function description"
    )


def is_valid_parameter_name(param_name: str) -> bool:
    """
    Check if a parameter name is valid, supporting both traditional and CLI-style names.
    
    Args:
        param_name: Parameter name to validate
    
    Returns:
        True if parameter name is valid, False otherwise
    """
    if not param_name or not isinstance(param_name, str):
        return False
    
    # Traditional Python identifier (original validation)
    if param_name.isidentifier():
        return True
    
    # CLI-style parameter patterns
    cli_patterns = [
        r'^-[a-zA-Z0-9]$',  # Single letter flags: -B, -A, -v
        r'^--[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$',  # Long flags: --long-name, --verbose
        r'^[a-zA-Z][a-zA-Z0-9_-]*[a-zA-Z0-9]$',  # kebab-case: my-param, long_name
    ]
    
    for pattern in cli_patterns:
        if re.match(pattern, param_name):
            return True
    
    return False


def normalize_parameter_name(param_name: str) -> str:
    """
    Normalize parameter names to a consistent format.
    
    Args:
        param_name: Original parameter name
    
    Returns:
        Normalized parameter name
    """
    if not param_name:
        return param_name
    
    # Remove leading dashes for internal processing
    normalized = param_name.lstrip('-')
    
    # Convert kebab-case to snake_case for internal consistency
    normalized = normalized.replace('-', '_')
    
    return normalized


def validate_enhanced_tool_definitions(tools: List[Dict[str, Any]], config: Optional[ToolCallingConfig] = None) -> List[ToolDefinition]:
    """
    Enhanced tool definition validation with better error handling and compatibility.
    
    Args:
        tools: List of tool definitions as dictionaries
        config: Optional tool calling configuration
    
    Returns:
        List of validated ToolDefinition objects
    
    Raises:
        ToolCallingValidationError: If tool definitions are invalid
    """
    if config is None:
        config = ToolCallingConfig()
    
    validated_tools = []
    validation_errors = []
    
    for i, tool_dict in enumerate(tools):
        try:
            # Attempt standard validation first
            tool_def = ToolDefinition(**tool_dict)
            
            # Additional enhanced validations
            if config.strict_parameter_validation:
                validate_function_parameters_enhanced(tool_def.function)
            
            # Check if function is allowed
            if not is_tool_allowed(tool_def.function.name, config):
                logger.warning(f"Function '{tool_def.function.name}' not allowed by configuration")
                continue
            
            validated_tools.append(tool_def)
            logger.debug(f"Successfully validated tool: {tool_def.function.name}")
            
        except Exception as e:
            error_msg = f"Tool '{tool_dict.get('function', {}).get('name', f'unknown_{i}')}' validation failed: {str(e)}"
            validation_errors.append(error_msg)
            logger.warning(error_msg)
            
            # If strict mode is off, try to create a minimal valid definition
            if not config.strict_parameter_validation:
                try:
                    minimal_tool = create_minimal_tool_definition(tool_dict)
                    validated_tools.append(minimal_tool)
                    logger.info(f"Created minimal tool definition for: {minimal_tool.function.name}")
                except Exception as fallback_error:
                    logger.error(f"Failed to create minimal tool definition: {fallback_error}")
    
    # If we have validation errors and no tools were validated, raise an exception
    if validation_errors and not validated_tools:
        raise ToolCallingValidationError(f"All tool definitions failed validation: {'; '.join(validation_errors)}")
    
    # Log warnings for any validation errors that occurred
    if validation_errors:
        logger.warning(f"Tool validation completed with {len(validation_errors)} errors, {len(validated_tools)} tools validated")
    
    return validated_tools


def validate_function_parameters_enhanced(function_def: FunctionDefinition) -> None:
    """
    Enhanced validation for function parameters with CLI-style support.
    
    Args:
        function_def: Function definition to validate
    
    Raises:
        ValueError: If parameters are invalid
    """
    for param_name, param_schema in function_def.parameters.properties.items():
        # Validate parameter name with enhanced rules
        if not is_valid_parameter_name(param_name):
            raise ValueError(f"Parameter name '{param_name}' is not valid. Must be a valid identifier or CLI-style parameter (e.g., '-B', '--long-name')")
        
        # Additional parameter type validation
        if param_schema.type == FunctionParameterType.ARRAY and param_schema.items is None:
            raise ValueError(f"Array parameter '{param_name}' must specify 'items' schema")
        
        if param_schema.type == FunctionParameterType.OBJECT and param_schema.properties is None:
            raise ValueError(f"Object parameter '{param_name}' must specify 'properties' schema")
        
        # Validate enum values if specified
        if param_schema.enum:
            if not isinstance(param_schema.enum, list) or len(param_schema.enum) == 0:
                raise ValueError(f"Enum parameter '{param_name}' must have non-empty array of allowed values")


def create_enhanced_tool_response(tool_call_id: str, result: Any, success: bool = True, error: Optional[str] = None, execution_time: float = 0.0) -> ToolResponse:
    """
    Create an enhanced tool response with additional metadata.
    
    Args:
        tool_call_id: ID of the tool call
        result: Result of the tool execution
        success: Whether execution was successful
        error: Error message if execution failed
        execution_time: Time taken for execution
    
    Returns:
        ToolResponse object with enhanced data
    """
    # Add some basic result validation/categorization
    result_type = type(result).__name__
    result_size = len(str(result)) if result is not None else 0
    
    logger.debug(f"Creating tool response for {tool_call_id}: success={success}, type={result_type}, size={result_size}")
    
    response = ToolResponse(
        success=success,
        result=result,
        error=error,
        execution_time=execution_time
    )
    
    return response


def format_enhanced_error_response(tool_call_id: str, error: Exception, execution_time: float = 0.0) -> ToolResponse:
    """
    Create an enhanced error response with detailed error information.
    
    Args:
        tool_call_id: ID of the tool call
        error: Exception that occurred
        execution_time: Time taken before error
    
    Returns:
        ToolResponse object with detailed error information
    """
    error_type = type(error).__name__
    error_message = str(error)
    
    # Create detailed error message
    detailed_error = f"{error_type}: {error_message}"
    logger.error(f"Tool {tool_call_id} failed: {detailed_error}")
    
    return ToolResponse(
        success=False,
        result=None,
        error=detailed_error,
        execution_time=execution_time
    )


def validate_tool_definitions(tools: List[Dict[str, Any]]) -> List[ToolDefinition]:
    """
    Validate and normalize tool definitions with OpenAI-compliant validation.
    
    This function uses a more permissive validation approach that accepts
    tool definitions that conform to the OpenAI API specification, even
    if we can't execute them locally.
    
    Args:
        tools: List of tool definitions as dictionaries
    
    Returns:
        List of validated ToolDefinition objects
    
    Raises:
        ValidationError: If tool definitions are fundamentally invalid
    """
    validated_tools = []
    
    for tool_dict in tools:
        try:
            # Use permissive validation that accepts OpenAI-compliant schemas
            tool_def = ToolDefinition(**tool_dict)
            validated_tools.append(tool_def)
            logger.debug(f"Validated tool definition: {tool_def.function.name}")
        except Exception as e:
            # For OpenAI compatibility, we should be more permissive
            # Log the error but don't fail - we'll let the client handle execution
            logger.warning(f"Tool definition validation issue for '{tool_dict.get('function', {}).get('name', 'unknown')}': {e}")
            # For now, still raise to maintain API contract, but this could be made more permissive
            # In a true passthrough mode, we would accept the tool definition anyway
            logger.info(f"Accepting tool definition despite validation issue (OpenAI passthrough compatibility)")
            try:
                # Try to create a minimal valid tool definition
                tool_def = create_minimal_tool_definition(tool_dict)
                validated_tools.append(tool_def)
            except Exception as fallback_error:
                logger.error(f"Failed to create minimal tool definition: {fallback_error}")
                # As a last resort, if we absolutely cannot validate, skip this tool
                # but continue processing others to maintain compatibility
                continue
    
    return validated_tools


def create_minimal_tool_definition(tool_dict: Dict[str, Any]) -> ToolDefinition:
    """
    Create a minimal valid tool definition from potentially problematic input.
    
    This is a fallback function that attempts to salvage a tool definition
    that has validation issues but is still structurally valid.
    
    Args:
        tool_dict: Original tool definition dictionary
    
    Returns:
        Minimal ToolDefinition object
    
    Raises:
        ValueError: If the tool definition is fundamentally invalid
    """
    # Extract the minimal required information
    function_dict = tool_dict.get('function', {})
    
    if not function_dict or 'name' not in function_dict:
        raise ValueError("Tool definition must contain a function with a name")
    
    # Create a minimal function definition
    minimal_function = FunctionDefinition(
        name=function_dict['name'][:64],  # Ensure max length
        description=function_dict.get('description', 'No description provided')[:1000],  # Reasonable length
    )
    
    # Create minimal tool definition
    minimal_tool = ToolDefinition(
        type="function",
        function=minimal_function
    )
    
    return minimal_tool


def validate_tool_choice(tool_choice: Optional[Union[str, Dict[str, Any]]]) -> Optional[ToolChoice]:
    """
    Validate and normalize tool choice specification.
    
    Args:
        tool_choice: Tool choice specification as string or dictionary
    
    Returns:
        Validated ToolChoice object or None
    
    Raises:
        ValidationError: If tool choice is invalid
    """
    if tool_choice is None:
        return None
    
    if isinstance(tool_choice, str):
        if tool_choice not in [tc.value for tc in ToolChoiceType]:
            raise ValueError(f"Invalid tool choice string: {tool_choice}")
        return ToolChoice(type=ToolChoiceType(tool_choice))
    
    elif isinstance(tool_choice, dict):
        return ToolChoice(**tool_choice)
    
    else:
        raise ValueError(f"Invalid tool choice type: {type(tool_choice)}")


def format_function_definitions(functions: List[FunctionDefinition]) -> str:
    """
    Format function definitions for prompt inclusion.
    
    Args:
        functions: List of function definitions
    
    Returns:
        Formatted string describing available functions
    """
    formatted_functions = []
    
    for func in functions:
        # Format parameters
        params_desc = []
        for param_name, param_schema in func.parameters.properties.items():
            required = param_name in (func.parameters.required or [])
            param_desc = f"{param_name} ({param_schema.type.value})"
            
            # Check if this is an n8n-style automatic parameter
            is_automatic = False
            if param_schema.description:
                if "Parameter value will be determined by the model automatically" in param_schema.description:
                    is_automatic = True
                elif "$fromAI(" in param_schema.description:
                    is_automatic = True
            
            if required:
                if is_automatic:
                    param_desc = f"[REQUIRED][AUTOMATIC] {param_desc} 🔸"
                else:
                    param_desc = f"[REQUIRED] {param_desc}"
            elif is_automatic:
                param_desc = f"[AUTOMATIC] {param_desc} 🔸"
            
            if param_schema.description:
                # Clean up n8n references for clarity
                clean_desc = param_schema.description
                if "$fromAI(" in clean_desc:
                    clean_desc = clean_desc.replace("$fromAI(", "").replace(")", "")
                    clean_desc = f"Context: {clean_desc}"
                param_desc += f" - {clean_desc}"
            
            if param_schema.enum:
                param_desc += f" [allowed: {param_schema.enum}]"
            if param_schema.default is not None:
                param_desc += f" (default: {param_schema.default})"
            
            params_desc.append(param_desc)
        
        param_str = ", ".join(params_desc) if params_desc else "no parameters"
        
        func_desc = f"**{func.name}**: {func.description or 'No description'}\n"
        func_desc += f" Parameters: {param_str}"
        
        # Add special instruction if function has automatic parameters
        if any("Parameter value will be determined by the model automatically" in 
               (schema.description or "") or "$fromAI(" in (schema.description or "")
               for schema in func.parameters.properties.values()):
            func_desc += "\n ⚠️ This function has parameters that require automatic value determination based on context."
        
        formatted_functions.append(func_desc)
    
    return "\n\n".join(formatted_functions)


def parse_tool_calls_from_response(response_text: str) -> List[Dict[str, Any]]:
    """
    Parse tool calls from model response text.
    
    Args:
        response_text: Raw response text from the model
    
    Returns:
        List of parsed tool call dictionaries
    
    Raises:
        ValueError: If tool calls cannot be parsed
    """
    tool_calls = []
    
    # Look for tool calls wrapped in specific tags
    start_tag = "<function_calls>"
    end_tag = "</function_calls>"
    
    start_idx = response_text.find(start_tag)
    end_idx = response_text.find(end_tag)
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        # Extract JSON between tags
        json_content = response_text[start_idx + len(start_tag):end_idx].strip()
        
        try:
            parsed_calls = json.loads(json_content)
            if isinstance(parsed_calls, list):
                for call in parsed_calls:
                    if isinstance(call, dict) and 'name' in call:
                        tool_calls.append(call)
                        logger.debug(f"Parsed tool call: {call}")
                    else:
                        logger.warning(f"Invalid tool call format: {call}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tool calls JSON: {e}, content: {json_content}")
            raise ValueError(f"Invalid JSON in tool calls: {e}")
    else:
        logger.debug("No tool calls found in response")
    
    return tool_calls


def create_tool_call_id() -> str:
    """
    Create a unique tool call ID.
    
    Returns:
        Unique string ID for tool call
    """
    return f"call_{uuid.uuid4().hex}"


def validate_tool_arguments(function_def: FunctionDefinition, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate tool arguments against function definition.
    
    Args:
        function_def: Function definition
        arguments: Arguments to validate
    
    Returns:
        Validated and normalized arguments
    
    Raises:
        ValueError: If arguments are invalid
    """
    validated_args = {}
    required_params = set(function_def.parameters.required or [])
    
    # Check required parameters
    missing_params = required_params - set(arguments.keys())
    if missing_params:
        raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
    
    # Validate each parameter
    for param_name, param_value in arguments.items():
        if param_name not in function_def.parameters.properties:
            logger.warning(f"Unknown parameter: {param_name}")
            continue
        
        param_schema = function_def.parameters.properties[param_name]
        
        # Type validation
        try:
            validated_value = validate_parameter_value(param_value, param_schema)
            validated_args[param_name] = validated_value
        except ValueError as e:
            raise ValueError(f"Invalid value for parameter '{param_name}': {e}")
    
    # Set defaults for missing optional parameters
    for param_name, param_schema in function_def.parameters.properties.items():
        if param_name not in validated_args and param_name not in required_params:
            if param_schema.default is not None:
                validated_args[param_name] = param_schema.default
    
    return validated_args


def validate_parameter_value(value: Any, param_schema: ParameterSchema) -> Any:
    """
    Validate a single parameter value against its schema.
    
    Args:
        value: Value to validate
        param_schema: Parameter schema
    
    Returns:
        Validated value
    
    Raises:
        ValueError: If value is invalid
    """
    if value is None:
        # Only allow None if it's explicitly a string "null" for some systems
        if param_schema.default is None:
            return None
        raise ValueError("Value cannot be null")
    
    param_type = param_schema.type
    
    if param_type == FunctionParameterType.STRING:
        return str(value)
    
    elif param_type == FunctionParameterType.NUMBER:
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Expected number, got {type(value).__name__}")
    
    elif param_type == FunctionParameterType.INTEGER:
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Expected integer, got {type(value).__name__}")
    
    elif param_type == FunctionParameterType.BOOLEAN:
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            if value.lower() in ['true', '1', 'yes', 'on']:
                return True
            elif value.lower() in ['false', '0', 'no', 'off']:
                return False
        raise ValueError(f"Expected boolean, got {type(value).__name__}")
    
    elif param_type == FunctionParameterType.ARRAY:
        if not isinstance(value, list):
            raise ValueError(f"Expected array, got {type(value).__name__}")
        
        if param_schema.items:
            # Validate array items if schema provided
            validated_items = []
            for item in value:
                # Create a temporary parameter schema for the item
                item_schema = ParameterSchema(type=param_schema.items.get('type', 'string'))
                validated_item = validate_parameter_value(item, item_schema)
                validated_items.append(validated_item)
            return validated_items
        return value
    
    elif param_type == FunctionParameterType.OBJECT:
        if not isinstance(value, dict):
            raise ValueError(f"Expected object, got {type(value).__name__}")
        
        # Basic object validation - could be enhanced with recursive validation
        return value
    
    else:
        # Unknown type, return as-is
        return value


def is_tool_allowed(function_name: str, config: ToolCallingConfig) -> bool:
    """
    Check if a function is allowed to be called.
    
    Args:
        function_name: Name of the function
        config: Tool calling configuration
    
    Returns:
        True if function is allowed, False otherwise
    """
    if config.allow_dangerous_functions:
        return True
    
    # List of potentially dangerous function names
    dangerous_patterns = [
        'exec', 'eval', 'system', 'shell', 'command', 'run',
        'delete', 'remove', 'destroy', 'format', 'wipe',
        'send', 'email', 'message', 'network', 'connect',
        'file', 'read', 'write', 'create', 'modify', 'download',
        'sudo', 'admin', 'root', 'password', 'secret', 'key'
    ]
    
    function_name_lower = function_name.lower()
    for pattern in dangerous_patterns:
        if pattern in function_name_lower:
            logger.warning(f"Function '{function_name}' matches dangerous pattern: {pattern}")
            return False
    
    return True


class ToolCallingSchemaError(Exception):
 """Exception raised for tool calling schema errors."""
 pass


class ToolCallingValidationError(Exception):
 """Exception raised for tool calling validation errors."""
 pass


class ToolExecutionError(Exception):
 """Exception raised for tool execution errors."""
 pass
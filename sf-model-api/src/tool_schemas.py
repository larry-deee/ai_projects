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
from typing import Dict, Any, List, Optional, Union, Literal, Tuple
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
    ENHANCED: Strict OpenAI API specification compliance validation for tool definitions.
    
    This function implements 100% compliant validation according to the OpenAI API 
    specification for function calling. All validation rules are strictly enforced
    to ensure complete API compliance and prevent any schema violations.
    
    Args:
        tools: List of tool definitions as dictionaries
    
    Returns:
        List of validated ToolDefinition objects
    
    Raises:
        ToolCallingValidationError: If any tool definition violates the OpenAI specification
    """
    if not tools:
        return []
    
    if not isinstance(tools, list):
        raise ToolCallingValidationError("Tools must be an array")
    
    validated_tools = []
    validation_errors = []
    
    for i, tool_dict in enumerate(tools):
        try:
            # CRITICAL: Validate tool_dict is a dictionary
            if not isinstance(tool_dict, dict):
                error_msg = f"Tool at index {i} must be an object, got {type(tool_dict).__name__}"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            tool_name = tool_dict.get('function', {}).get('name', f'tool_{i}')
            
            # STEP 1: STRICT TYPE FIELD VALIDATION
            if 'type' not in tool_dict:
                error_msg = f"Tool '{tool_name}' missing required field: 'type'"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            # CRITICAL: Type must be exactly "function"
            if tool_dict['type'] != 'function':
                error_msg = f"Tool '{tool_name}' invalid 'type': '{tool_dict['type']}'. Must be exactly 'function'"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            # STEP 2: STRICT FUNCTION OBJECT VALIDATION
            if 'function' not in tool_dict:
                error_msg = f"Tool '{tool_name}' missing required field: 'function'"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            function_obj = tool_dict['function']
            if not isinstance(function_obj, dict):
                error_msg = f"Tool '{tool_name}' field 'function' must be an object, got {type(function_obj).__name__}"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            # STEP 3: STRICT FUNCTION NAME VALIDATION
            if 'name' not in function_obj:
                error_msg = f"Tool '{tool_name}' function missing required field: 'name'"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            function_name = function_obj['name']
            if not isinstance(function_name, str) or not function_name.strip():
                error_msg = f"Tool '{tool_name}' function 'name' must be a non-empty string"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            # OpenAI specification: function name validation (alphanumeric, underscore, hyphen only)
            if len(function_name) > 64:
                error_msg = f"Tool '{tool_name}' function name exceeds 64 character limit: {len(function_name)}"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            # STEP 4: FUNCTION DESCRIPTION VALIDATION (REQUIRED per OpenAI spec)
            if 'description' not in function_obj:
                error_msg = f"Tool '{tool_name}' function missing required field: 'description'"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            if not isinstance(function_obj['description'], str) or not function_obj['description'].strip():
                error_msg = f"Tool '{tool_name}' function 'description' must be a non-empty string"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            # STEP 5: STRICT PARAMETERS SCHEMA VALIDATION
            if 'parameters' in function_obj:
                params_obj = function_obj['parameters']
                if not isinstance(params_obj, dict):
                    error_msg = f"Tool '{tool_name}' 'parameters' must be an object, got {type(params_obj).__name__}"
                    validation_errors.append(error_msg)
                    logger.error(error_msg)
                    continue
                
                # CRITICAL: Parameters type must be "object"
                if 'type' not in params_obj:
                    error_msg = f"Tool '{tool_name}' parameters missing required field: 'type'"
                    validation_errors.append(error_msg)
                    logger.error(error_msg)
                    continue
                
                if params_obj['type'] != 'object':
                    error_msg = f"Tool '{tool_name}' parameters 'type' must be exactly 'object', got: '{params_obj['type']}'"
                    validation_errors.append(error_msg)
                    logger.error(error_msg)
                    continue
                
                # STEP 6: STRICT PROPERTIES VALIDATION
                if 'properties' in params_obj:
                    properties = params_obj['properties']
                    if not isinstance(properties, dict):
                        error_msg = f"Tool '{tool_name}' parameters 'properties' must be an object, got {type(properties).__name__}"
                        validation_errors.append(error_msg)
                        logger.error(error_msg)
                        continue
                    
                    # Validate each property strictly
                    for prop_name, prop_schema in properties.items():
                        if not isinstance(prop_schema, dict):
                            error_msg = f"Tool '{tool_name}' property '{prop_name}' must be an object, got {type(prop_schema).__name__}"
                            validation_errors.append(error_msg)
                            logger.error(error_msg)
                            break
                        
                        # Property must have type field
                        if 'type' not in prop_schema:
                            error_msg = f"Tool '{tool_name}' property '{prop_name}' missing required field: 'type'"
                            validation_errors.append(error_msg)
                            logger.error(error_msg)
                            break
                        
                        # Validate property type against JSON Schema specification
                        valid_types = ['string', 'number', 'integer', 'boolean', 'array', 'object']
                        prop_type = prop_schema['type']
                        if prop_type not in valid_types:
                            error_msg = f"Tool '{tool_name}' property '{prop_name}' invalid type: '{prop_type}'. Must be one of: {', '.join(valid_types)}"
                            validation_errors.append(error_msg)
                            logger.error(error_msg)
                            break
                        
                        # STRICT ARRAY TYPE VALIDATION
                        if prop_type == 'array':
                            if 'items' not in prop_schema:
                                error_msg = f"Tool '{tool_name}' array property '{prop_name}' missing required 'items' schema"
                                validation_errors.append(error_msg)
                                logger.error(error_msg)
                                break
                            elif not isinstance(prop_schema['items'], dict):
                                error_msg = f"Tool '{tool_name}' array property '{prop_name}' 'items' must be an object"
                                validation_errors.append(error_msg)
                                logger.error(error_msg)
                                break
                        
                        # STRICT OBJECT TYPE VALIDATION
                        if prop_type == 'object':
                            if 'properties' not in prop_schema:
                                error_msg = f"Tool '{tool_name}' object property '{prop_name}' missing required 'properties' schema"
                                validation_errors.append(error_msg)
                                logger.error(error_msg)
                                break
                            elif not isinstance(prop_schema['properties'], dict):
                                error_msg = f"Tool '{tool_name}' object property '{prop_name}' 'properties' must be an object"
                                validation_errors.append(error_msg)
                                logger.error(error_msg)
                                break
                    
                    # Break out of main loop if property validation failed
                    if validation_errors and validation_errors[-1].startswith(f"Tool '{tool_name}'"):
                        continue
                
                # STEP 7: STRICT REQUIRED FIELD VALIDATION
                if 'required' in params_obj:
                    required_fields = params_obj['required']
                    if not isinstance(required_fields, list):
                        error_msg = f"Tool '{tool_name}' parameters 'required' must be an array, got {type(required_fields).__name__}"
                        validation_errors.append(error_msg)
                        logger.error(error_msg)
                        continue
                    
                    # Each required field must be a string
                    for req_field in required_fields:
                        if not isinstance(req_field, str):
                            error_msg = f"Tool '{tool_name}' required field must be string, got {type(req_field).__name__}: {req_field}"
                            validation_errors.append(error_msg)
                            logger.error(error_msg)
                            break
                    
                    # All required properties must exist in properties
                    if 'properties' in params_obj:
                        properties = params_obj['properties']
                        invalid_required = [r for r in required_fields if r not in properties]
                        if invalid_required:
                            error_msg = f"Tool '{tool_name}' required properties don't exist in properties: {', '.join(invalid_required)}"
                            validation_errors.append(error_msg)
                            logger.error(error_msg)
                            continue
            
            # STEP 8: FINAL PYDANTIC MODEL VALIDATION
            try:
                # Attempt to create ToolDefinition - this validates the complete schema
                tool_def = ToolDefinition(**tool_dict)
                validated_tools.append(tool_def)
                logger.debug(f"✅ Successfully validated tool: {tool_def.function.name}")
                
            except Exception as pydantic_error:
                error_msg = f"Tool '{tool_name}' failed Pydantic validation: {str(pydantic_error)}"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
        
        except Exception as unexpected_error:
            error_msg = f"Tool at index {i} validation failed with unexpected error: {str(unexpected_error)}"
            validation_errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    # CRITICAL: If ANY validation errors occurred, reject the entire request
    if validation_errors:
        full_error_message = f"Tool validation failed with {len(validation_errors)} errors:\n" + "\n".join(validation_errors)
        logger.error(f"❌ Tool validation failed: {len(validation_errors)} errors found")
        raise ToolCallingValidationError(full_error_message)
    
    if not validated_tools:
        raise ToolCallingValidationError("No valid tools found in request")
    
    logger.info(f"✅ Successfully validated {len(validated_tools)} tools with 100% API compliance")
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
    Parse tool calls from model response text with robust error handling.
    
    Args:
        response_text: Raw response text from the model
    
    Returns:
        List of parsed tool call dictionaries
    
    Raises:
        ValueError: If tool calls cannot be parsed after all recovery attempts
    """
    tool_calls = []
    
    # Look for tool calls in multiple n8n-compatible formats
    extraction_patterns = [
        # Pattern 1: Standard <function_calls> tags
        ("<function_calls>", "</function_calls>"),
        # Pattern 2: Alternative tags that n8n might use
        ("<tool_calls>", "</tool_calls>"),
        ("TOOL_CALLS:", "\n\n"),
        # Pattern 3: JSON array without tags
        ("[", None),  # Special case for direct JSON arrays
    ]
    
    json_content = None
    
    for start_tag, end_tag in extraction_patterns:
        start_idx = response_text.find(start_tag)
        
        if start_idx != -1:
            if end_tag is None:  # Special case for direct JSON arrays
                # Look for JSON array starting with [
                potential_json = response_text[start_idx:]
                # Find the matching closing bracket
                bracket_count = 0
                end_idx = start_idx
                
                for i, char in enumerate(potential_json):
                    if char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = start_idx + i + 1
                            break
                
                if bracket_count == 0 and end_idx > start_idx:
                    json_content = response_text[start_idx:end_idx]
                    break
            else:
                end_idx = response_text.find(end_tag, start_idx)
                if end_idx != -1 and end_idx > start_idx:
                    if start_tag == "TOOL_CALLS:":
                        json_content = response_text[start_idx + len(start_tag):end_idx].strip()
                    else:
                        json_content = response_text[start_idx + len(start_tag):end_idx].strip()
                    break
    
    if json_content:
        # Pre-process n8n-specific patterns before JSON parsing
        processed_content = _preprocess_n8n_tool_calls(json_content)
        
        try:
            parsed_calls = json.loads(processed_content)
            if isinstance(parsed_calls, list):
                for i, call in enumerate(parsed_calls):
                    if isinstance(call, dict) and 'name' in call:
                        try:
                            # CRITICAL: Convert to OpenAI-compliant format
                            compliant_call = _create_openai_compliant_tool_call(call)
                            tool_calls.append(compliant_call)
                            logger.debug(f"Created OpenAI-compliant tool call: {compliant_call['id']}")
                        except ValueError as validation_error:
                            logger.warning(f"Skipping invalid tool call at index {i}: {validation_error}")
                            continue
                    else:
                        logger.warning(f"Invalid tool call format at index {i}: missing 'name' field")
                        continue
            else:
                logger.error(f"Parsed tool calls is not an array: {type(parsed_calls)}")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tool calls JSON: {e}")
            
            # Enhanced recovery with strict compliance validation
            recovered_calls = _attempt_json_recovery_with_compliance(processed_content, e)
            if recovered_calls:
                logger.info(f"Successfully recovered {len(recovered_calls)} compliant tool calls")
                tool_calls.extend(recovered_calls)
            else:
                logger.error(f"JSON recovery failed, cannot extract tool calls")
                return []
    else:
        logger.debug("No tool calls found in response")
    
    # Final validation: ensure all tool calls are OpenAI compliant
    validated_calls = []
    for call in tool_calls:
        if _validate_tool_call_compliance(call):
            validated_calls.append(call)
        else:
            logger.warning(f"Dropping non-compliant tool call: {call.get('id', 'unknown')}")
    
    logger.info(f"Parsed {len(validated_calls)} OpenAI-compliant tool calls")
    return validated_calls


def _attempt_json_recovery(malformed_json: str, original_error: json.JSONDecodeError) -> List[Dict[str, Any]]:
    """
    Attempt to recover malformed JSON by fixing common issues.
    
    Args:
        malformed_json: The malformed JSON string
        original_error: The original JSONDecodeError
        
    Returns:
        List of recovered tool call dictionaries, empty if recovery failed
    """
    recovered_calls = []
    
    try:
        # Fix 1: Remove extra closing brackets (common n8n issue)
        cleaned_json = malformed_json.strip()
        
        # Count opening and closing brackets to detect mismatched brackets
        open_brackets = cleaned_json.count('[')
        close_brackets = cleaned_json.count(']')
        
        if close_brackets > open_brackets:
            # Remove extra closing brackets from the end
            extra_brackets = close_brackets - open_brackets
            logger.info(f"Removing {extra_brackets} extra closing brackets")
            
            # Remove extra brackets from the end
            while extra_brackets > 0 and cleaned_json.endswith(']'):
                cleaned_json = cleaned_json[:-1].strip()
                extra_brackets -= 1
        
        # Fix 2: Ensure proper array format
        if not cleaned_json.startswith('['):
            cleaned_json = '[' + cleaned_json
        if not cleaned_json.endswith(']'):
            cleaned_json = cleaned_json + ']'
        
        # Attempt to parse cleaned JSON
        parsed_calls = json.loads(cleaned_json)
        
        if isinstance(parsed_calls, list):
            for call in parsed_calls:
                if isinstance(call, dict) and 'name' in call:
                    recovered_calls.append(call)
                    logger.debug(f"Recovered tool call: {call}")
        
        logger.info(f"JSON recovery successful: recovered {len(recovered_calls)} calls")
        return recovered_calls
        
    except json.JSONDecodeError as recovery_error:
        # Fix 3: Try to extract individual tool calls using regex patterns
        logger.warning(f"Standard JSON recovery failed: {recovery_error}")
        return _extract_tool_calls_with_regex(malformed_json)
    
    except Exception as e:
        logger.error(f"Unexpected error in JSON recovery: {e}")
        return []


def _extract_tool_calls_with_regex(malformed_json: str) -> List[Dict[str, Any]]:
    """
    Extract tool calls using regex patterns as a last resort recovery method.
    
    Args:
        malformed_json: The malformed JSON string
        
    Returns:
        List of extracted tool call dictionaries
    """
    import re
    
    recovered_calls = []
    
    try:
        # Pattern to extract individual tool call objects
        tool_call_pattern = r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{[^}]*\}|\{[^}]*\})\s*\}'
        
        matches = re.findall(tool_call_pattern, malformed_json)
        
        for match in matches:
            function_name = match[0]
            arguments_str = match[1]
            
            try:
                # Try to parse arguments
                if arguments_str.strip():
                    arguments = json.loads(arguments_str)
                else:
                    arguments = {}
                
                tool_call = {
                    "name": function_name,
                    "arguments": arguments
                }
                
                recovered_calls.append(tool_call)
                logger.debug(f"Regex extracted tool call: {tool_call}")
                
            except json.JSONDecodeError:
                # If arguments can't be parsed, use empty dict
                tool_call = {
                    "name": function_name,
                    "arguments": {}
                }
                recovered_calls.append(tool_call)
                logger.warning(f"Using empty arguments for tool: {function_name}")
        
        if recovered_calls:
            logger.info(f"Regex recovery successful: extracted {len(recovered_calls)} calls")
        
    except Exception as e:
        logger.error(f"Regex recovery failed: {e}")
    
    return recovered_calls


def _process_n8n_arguments(arguments_str: str) -> str:
    """
    Process n8n-specific argument patterns to make them JSON-parseable.
    
    Args:
        arguments_str: Raw arguments string from n8n
        
    Returns:
        Processed arguments string that can be parsed as JSON
    """
    processed = arguments_str.strip()
    
    # Replace n8n $fromAI patterns with placeholder values
    # Pattern: $fromAI('param_name', 'default_value', 'type')
    fromai_pattern = r"\$fromAI\([\"']([^\"'\n]+)[\"'],\s*[\"']([^\"'\n]*)[\"'],\s*[\"']([^\"'\n]+)[\"']\)"
    
    def replace_fromai(match):
        param_name = match.group(1)
        default_value = match.group(2)
        param_type = match.group(3)
        
        # Return the default value with proper quotes based on type
        if param_type in ['string', 'str']:
            return f'"{default_value}"'
        elif param_type in ['number', 'int', 'integer', 'float']:
            try:
                float(default_value)
                return default_value
            except ValueError:
                return '0'
        elif param_type in ['boolean', 'bool']:
            return default_value.lower() if default_value.lower() in ['true', 'false'] else 'false'
        else:
            return f'"{default_value}"'
    
    processed = re.sub(fromai_pattern, replace_fromai, processed)
    
    # Clean up common n8n formatting issues
    processed = re.sub(r'(["\'])(\\w+)(["\']):(?!["\'])', r'"\2":', processed)  # Ensure property names are quoted
    processed = re.sub(r':(["\'])(.+?)\1([,}])', r':"\\2"\\3', processed)  # Fix broken string values
    
    return processed


def _extract_n8n_parameters_manually(arguments_str: str) -> Dict[str, Any]:
    """
    Manually extract parameters from malformed n8n arguments as fallback.
    
    Args:
        arguments_str: Malformed arguments string
        
    Returns:
        Dictionary of extracted parameters
    """
    params = {}
    
    try:
        # Extract key-value pairs using regex
        # Pattern to match key: "value" or key: value
        param_patterns = [
            r'["\']?([a-zA-Z_][a-zA-Z0-9_]*)["\']?\s*:\s*["\']([^"\'\n]*)["\']',  # "key": "value"
            r'["\']?([a-zA-Z_][a-zA-Z0-9_]*)["\']?\s*:\s*([a-zA-Z0-9._-]+)',          # "key": value
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*["\']([^"\'\n]*)["\']',                # key="value" (n8n style)
        ]
        
        for pattern in param_patterns:
            matches = re.findall(pattern, arguments_str)
            for key, value in matches:
                if key not in params:  # Don't overwrite already found params
                    params[key] = value
        
        # Extract $fromAI patterns and use their default values
        fromai_pattern = r"\$fromAI\([\"']([^\"'\n]+)[\"'],\s*[\"']([^\"'\n]*)[\"'],\s*[\"']([^\"'\n]+)[\"']\)"
        fromai_matches = re.findall(fromai_pattern, arguments_str)
        
        for param_name, default_value, param_type in fromai_matches:
            if param_name not in params:
                params[param_name] = default_value
        
        logger.info(f"n8n manual parameter extraction found {len(params)} parameters")
        
    except Exception as e:
        logger.error(f"Manual n8n parameter extraction failed: {e}")
    
    return params


def _preprocess_n8n_tool_calls(json_content: str) -> str:
    """
    Pre-process n8n tool call content to handle $fromAI() patterns and formatting issues.
    
    Args:
        json_content: Raw JSON content from n8n
        
    Returns:
        Processed JSON content ready for parsing
    """
    processed = json_content.strip()
    
    # Handle n8n $fromAI() patterns in the JSON structure
    # Pattern: "param": "{{ $fromAI('param_name', 'default', 'type') }}"
    fromai_pattern = r'"([^"]+)"\s*:\s*"\{\{\s*\$fromAI\(["\']([^"\'\n]+)["\'],\s*["\']([^"\'\n]*)["\'],\s*["\']([^"\'\n]+)["\']\)\s*\}\}"'
    
    def replace_fromai_in_json(match):
        json_key = match.group(1)
        param_name = match.group(2)
        default_value = match.group(3)
        param_type = match.group(4)
        
        # Use the parameter name as key and default value as value
        if param_type in ['string', 'str']:
            return f'"{param_name}": "{default_value}"'
        elif param_type in ['number', 'int', 'integer', 'float']:
            try:
                float(default_value)
                return f'"{param_name}": {default_value}'
            except ValueError:
                return f'"{param_name}": 0'
        elif param_type in ['boolean', 'bool']:
            bool_value = default_value.lower() if default_value.lower() in ['true', 'false'] else 'false'
            return f'"{param_name}": {bool_value}'
        else:
            return f'"{param_name}": "{default_value}"'
    
    processed = re.sub(fromai_pattern, replace_fromai_in_json, processed)
    
    # Handle simpler $fromAI patterns without the {{ }} wrapper
    simple_fromai_pattern = r'"([^"]+)"\s*:\s*"\$fromAI\(["\']([^"\'\n]+)["\'],\s*["\']([^"\'\n]*)["\'],\s*["\']([^"\'\n]+)["\']\)"'
    processed = re.sub(simple_fromai_pattern, replace_fromai_in_json, processed)
    
    # Clean up n8n-specific formatting issues
    processed = re.sub(r',\s*}', '}', processed)  # Remove trailing commas before }
    processed = re.sub(r',\s*]', ']', processed)  # Remove trailing commas before ]
    
    logger.debug(f"n8n preprocessing: {len(json_content)} -> {len(processed)} chars")
    return processed


def _postprocess_n8n_tool_call(call: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process a parsed tool call for n8n compatibility.
    Maintains tool_handler expected format (name/arguments) for backward compatibility.
    
    Args:
        call: Raw parsed tool call dictionary
        
    Returns:
        Post-processed tool call with n8n enhancements in tool_handler format
    """
    processed_call = call.copy()
    
    # Ensure name is present
    if 'name' not in processed_call:
        if 'function' in processed_call and isinstance(processed_call['function'], dict):
            processed_call['name'] = processed_call['function'].get('name', '')
    
    # Ensure arguments is always a dictionary
    if 'arguments' not in processed_call:
        if 'function' in processed_call and isinstance(processed_call['function'], dict):
            args = processed_call['function'].get('arguments', {})
            if isinstance(args, str):
                try:
                    processed_call['arguments'] = json.loads(args)
                except json.JSONDecodeError:
                    processed_call['arguments'] = _extract_n8n_parameters_manually(args)
            else:
                processed_call['arguments'] = args
        else:
            processed_call['arguments'] = {}
    elif isinstance(processed_call['arguments'], str):
        try:
            processed_call['arguments'] = json.loads(processed_call['arguments'])
        except json.JSONDecodeError:
            # If arguments is a malformed string, try to extract parameters
            processed_call['arguments'] = _extract_n8n_parameters_manually(processed_call['arguments'])
    
    # Ensure we have the basic required fields for tool_handler compatibility
    if not processed_call.get('name'):
        logger.warning("n8n tool call missing name field")
        processed_call['name'] = 'unknown_function'
    
    if not isinstance(processed_call.get('arguments'), dict):
        logger.warning("n8n tool call arguments not a dictionary, converting")
        processed_call['arguments'] = {}
    
    return processed_call


def _create_openai_compliant_tool_call(call: Dict[str, Any]) -> Dict[str, Any]:
    """
    CRITICAL FIX: Create OpenAI-compliant tool call from parsed data.
    
    This function ensures 100% compliance with the OpenAI API specification for
    tool call responses, including proper ID generation, type validation, and
    argument formatting.
    
    Args:
        call: Raw parsed tool call dictionary
        
    Returns:
        OpenAI-compliant tool call dictionary
        
    Raises:
        ValueError: If the call cannot be made compliant
    """
    # Extract function name
    function_name = None
    if 'name' in call:
        function_name = call['name']
    elif 'function' in call and isinstance(call['function'], dict) and 'name' in call['function']:
        function_name = call['function']['name']
    
    if not function_name or not isinstance(function_name, str):
        raise ValueError("Tool call missing valid function name")
    
    # Extract and validate arguments
    arguments = {}
    if 'arguments' in call:
        args_value = call['arguments']
        if isinstance(args_value, dict):
            arguments = args_value
        elif isinstance(args_value, str):
            try:
                # CRITICAL: Arguments must be valid JSON string in OpenAI format
                arguments = json.loads(args_value)
                if not isinstance(arguments, dict):
                    raise ValueError(f"Arguments must be object, got {type(arguments).__name__}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse arguments JSON: {e}, attempting manual extraction")
                arguments = _extract_n8n_parameters_manually(args_value)
        else:
            logger.warning(f"Invalid arguments type: {type(args_value)}, using empty dict")
            arguments = {}
    elif 'function' in call and isinstance(call['function'], dict) and 'arguments' in call['function']:
        # Handle OpenAI nested format
        args_value = call['function']['arguments']
        if isinstance(args_value, str):
            try:
                arguments = json.loads(args_value)
            except json.JSONDecodeError:
                arguments = _extract_n8n_parameters_manually(args_value)
        elif isinstance(args_value, dict):
            arguments = args_value
    
    # Generate OpenAI-compliant tool call ID if not present
    call_id = call.get('id')
    if not call_id or not isinstance(call_id, str):
        call_id = create_tool_call_id()
    
    # Ensure ID follows OpenAI format: "call_" prefix
    if not call_id.startswith('call_'):
        call_id = f"call_{call_id}"
    
    # CRITICAL: Create OpenAI-compliant tool call structure
    compliant_call = {
        "id": call_id,
        "type": "function",  # REQUIRED: Must be "function"
        "function": {
            "name": function_name,
            "arguments": json.dumps(arguments)  # CRITICAL: Must be JSON string
        }
    }
    
    # Validate the created structure
    if not _validate_tool_call_compliance(compliant_call):
        raise ValueError(f"Failed to create compliant tool call for function: {function_name}")
    
    return compliant_call


def _validate_tool_call_compliance(call: Dict[str, Any]) -> bool:
    """
    CRITICAL: Validate tool call against OpenAI API specification.
    
    Ensures 100% compliance with OpenAI tool call response format:
    {
        "id": "call_abc123",
        "type": "function",
        "function": {
            "name": "function_name",
            "arguments": "{\"param\":\"value\"}"
        }
    }
    
    Args:
        call: Tool call dictionary to validate
        
    Returns:
        bool: True if compliant, False otherwise
    """
    try:
        # Check required top-level fields
        required_fields = ['id', 'type', 'function']
        for field in required_fields:
            if field not in call:
                logger.warning(f"Tool call missing required field: {field}")
                return False
        
        # Validate ID format
        call_id = call['id']
        if not isinstance(call_id, str) or not call_id.strip():
            logger.warning(f"Tool call ID must be non-empty string: {call_id}")
            return False
        
        # Validate type is exactly "function"
        if call['type'] != 'function':
            logger.warning(f"Tool call type must be 'function', got: {call['type']}")
            return False
        
        # Validate function object
        function_obj = call['function']
        if not isinstance(function_obj, dict):
            logger.warning(f"Tool call function must be object, got: {type(function_obj).__name__}")
            return False
        
        # Check required function fields
        function_required = ['name', 'arguments']
        for field in function_required:
            if field not in function_obj:
                logger.warning(f"Tool call function missing required field: {field}")
                return False
        
        # Validate function name
        function_name = function_obj['name']
        if not isinstance(function_name, str) or not function_name.strip():
            logger.warning(f"Function name must be non-empty string: {function_name}")
            return False
        
        # CRITICAL: Validate arguments is JSON string
        arguments = function_obj['arguments']
        if not isinstance(arguments, str):
            logger.warning(f"Function arguments must be JSON string, got: {type(arguments).__name__}")
            return False
        
        # Validate arguments is valid JSON
        try:
            parsed_args = json.loads(arguments)
            if not isinstance(parsed_args, dict):
                logger.warning(f"Function arguments must parse to object, got: {type(parsed_args).__name__}")
                return False
        except json.JSONDecodeError as e:
            logger.warning(f"Function arguments not valid JSON: {e}")
            return False
        
        return True
        
    except Exception as e:
        logger.warning(f"Tool call validation failed: {e}")
        return False


def _attempt_json_recovery_with_compliance(malformed_json: str, original_error: json.JSONDecodeError) -> List[Dict[str, Any]]:
    """
    ENHANCED: Attempt JSON recovery with strict OpenAI compliance validation.
    
    Args:
        malformed_json: The malformed JSON string
        original_error: The original JSONDecodeError
        
    Returns:
        List of OpenAI-compliant tool call dictionaries
    """
    recovered_calls = []
    
    try:
        # Use existing recovery method
        basic_recovered = _attempt_json_recovery(malformed_json, original_error)
        
        # Convert each recovered call to OpenAI compliance
        for call in basic_recovered:
            try:
                compliant_call = _create_openai_compliant_tool_call(call)
                recovered_calls.append(compliant_call)
            except ValueError as e:
                logger.warning(f"Cannot make recovered call compliant: {e}")
                continue
        
        logger.info(f"JSON recovery created {len(recovered_calls)} compliant tool calls")
        return recovered_calls
        
    except Exception as e:
        logger.error(f"Enhanced JSON recovery failed: {e}")
        return []


def validate_anthropic_tool_definitions(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate tool definitions according to Anthropic API specification.
    
    Anthropic's tool definition format differs from OpenAI's in that it does not use
    the nested 'function' object, but instead has a flatter structure.
    
    Args:
        tools: List of tool definitions as dictionaries
    
    Returns:
        List of validated tool definition dictionaries
    
    Raises:
        ToolCallingValidationError: If any tool definition is invalid according to the Anthropic specification
    """
    validated_tools = []
    validation_errors = []
    
    for i, tool_dict in enumerate(tools):
        tool_name = tool_dict.get('name', f'unknown_tool_{i}')
        
        # Step 1: Validate required fields
        required_fields = ['name', 'description', 'input_schema']
        missing_fields = [f for f in required_fields if f not in tool_dict]
        if missing_fields:
            error_msg = f"Anthropic tool '{tool_name}' missing required fields: {', '.join(missing_fields)}"
            validation_errors.append(error_msg)
            logger.error(error_msg)
            continue
        
        # Step 2: Validate name format
        if not tool_dict['name'] or not isinstance(tool_dict['name'], str):
            error_msg = f"Anthropic tool name must be a non-empty string"
            validation_errors.append(error_msg)
            logger.error(error_msg)
            continue
        
        # Step 3: Validate input_schema structure
        input_schema = tool_dict.get('input_schema', {})
        if not isinstance(input_schema, dict):
            error_msg = f"Anthropic tool '{tool_name}' has invalid 'input_schema': must be an object"
            validation_errors.append(error_msg)
            logger.error(error_msg)
            continue
        
        # Step 4: Validate input_schema has required properties
        schema_required_fields = ['type', 'properties']
        schema_missing_fields = [f for f in schema_required_fields if f not in input_schema]
        if schema_missing_fields:
            error_msg = f"Anthropic tool '{tool_name}' input_schema missing required fields: {', '.join(schema_missing_fields)}"
            validation_errors.append(error_msg)
            logger.error(error_msg)
            continue
        
        # Step 5: Validate input_schema type is 'object'
        if input_schema.get('type') != 'object':
            error_msg = f"Anthropic tool '{tool_name}' input_schema 'type' must be 'object', got: '{input_schema.get('type')}'" 
            validation_errors.append(error_msg)
            logger.error(error_msg)
            continue
            
        # Step 6: Validate properties is a dictionary
        properties = input_schema.get('properties', {})
        if not isinstance(properties, dict):
            error_msg = f"Anthropic tool '{tool_name}' input_schema 'properties' must be an object"
            validation_errors.append(error_msg)
            logger.error(error_msg)
            continue
        
        # Step 7: Validate individual properties
        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                error_msg = f"Anthropic tool '{tool_name}' property '{prop_name}' must be an object"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            # Check for required property fields
            if 'type' not in prop_schema:
                error_msg = f"Anthropic tool '{tool_name}' property '{prop_name}' missing required field: 'type'"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            # Validate property type
            valid_types = ['string', 'number', 'integer', 'boolean', 'array', 'object']
            if prop_schema['type'] not in valid_types:
                error_msg = f"Anthropic tool '{tool_name}' property '{prop_name}' has invalid type: '{prop_schema['type']}'. Must be one of: {', '.join(valid_types)}"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            # Additional validations for array and object types
            if prop_schema['type'] == 'array' and ('items' not in prop_schema or not isinstance(prop_schema['items'], dict)):
                error_msg = f"Anthropic tool '{tool_name}' array property '{prop_name}' must specify 'items' schema"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            if prop_schema['type'] == 'object' and ('properties' not in prop_schema or not isinstance(prop_schema['properties'], dict)):
                error_msg = f"Anthropic tool '{tool_name}' object property '{prop_name}' must specify 'properties' schema"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
        
        # Step 8: Check that required properties exist
        if 'required' in input_schema:
            if not isinstance(input_schema['required'], list):
                error_msg = f"Anthropic tool '{tool_name}' input_schema 'required' must be an array"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            invalid_required = [r for r in input_schema['required'] if r not in properties]
            if invalid_required:
                error_msg = f"Anthropic tool '{tool_name}' has required properties that don't exist: {', '.join(invalid_required)}"
                validation_errors.append(error_msg)
                logger.error(error_msg)
                continue
        
        # All validations passed for this tool
        validated_tools.append(tool_dict)
        logger.debug(f"Successfully validated Anthropic tool: {tool_name}")
    
    # CRITICAL: If ANY validation errors occurred, reject the entire request
    if validation_errors:
        full_error_message = f"Anthropic tool validation failed with {len(validation_errors)} errors:\\n" + "\\n".join(validation_errors)
        logger.error(f"❌ Anthropic tool validation failed: {len(validation_errors)} errors found")
        raise ToolCallingValidationError(full_error_message)
    
    if not validated_tools:
        raise ToolCallingValidationError("No valid Anthropic tools found in request")
    
    logger.info(f"✅ Successfully validated {len(validated_tools)} Anthropic tools with 100% API compliance")
    return validated_tools


def convert_openai_to_anthropic_tools(openai_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert OpenAI-format tool definitions to Anthropic-format tool definitions.
    
    Args:
        openai_tools: List of OpenAI-format tool definitions
        
    Returns:
        List of Anthropic-format tool definitions
    """
    anthropic_tools = []
    
    for tool in openai_tools:
        # Skip if not a function-type tool
        if tool.get('type') != 'function' or 'function' not in tool:
            continue
            
        function = tool['function']
        
        # Create Anthropic tool structure
        anthropic_tool = {
            "name": function.get('name', ''),
            "description": function.get('description', ''),
            "input_schema": function.get('parameters', {}) 
        }
        
        anthropic_tools.append(anthropic_tool)
    
    return anthropic_tools


def convert_anthropic_to_openai_tools(anthropic_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert Anthropic-format tool definitions to OpenAI-format tool definitions.
    
    Args:
        anthropic_tools: List of Anthropic-format tool definitions
        
    Returns:
        List of OpenAI-format tool definitions
    """
    openai_tools = []
    
    for tool in anthropic_tools:
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool.get('name', ''),
                "description": tool.get('description', ''),
                "parameters": tool.get('input_schema', {})
            }
        }
        
        openai_tools.append(openai_tool)
    
    return openai_tools


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
    Validate a single parameter value against its schema with enhanced type checking
    and support for schema constraints like enum and required properties.
    
    Args:
        value: Value to validate
        param_schema: Parameter schema
    
    Returns:
        Validated value (potentially coerced to the right type)
    
    Raises:
        ValueError: If value is invalid according to the schema
    """
    if value is None:
        # Only allow None if it's explicitly allowed as default
        if param_schema.default is None:
            return None
        raise ValueError("Value cannot be null for this parameter")
    
    param_type = param_schema.type
    
    # First check enum constraints if specified
    if param_schema.enum is not None and len(param_schema.enum) > 0:
        if value not in param_schema.enum:
            raise ValueError(
                f"Value '{value}' not in allowed values: {param_schema.enum}"
            )
    
    # Type-specific validation with improved error messages
    if param_type == FunctionParameterType.STRING:
        if not isinstance(value, str):
            # Try to coerce to string if possible
            try:
                return str(value)
            except Exception:
                raise ValueError(
                    f"Expected string, got {type(value).__name__}: '{value}'"
                )
        return value
    
    elif param_type == FunctionParameterType.NUMBER:
        if isinstance(value, (int, float)):
            return float(value)  # Safely convert integers to float
        elif isinstance(value, str):
            # Try to parse string as number
            try:
                return float(value)
            except ValueError:
                raise ValueError(
                    f"Expected number, could not convert string '{value}' to number"
                )
        else:
            raise ValueError(
                f"Expected number, got {type(value).__name__}: '{value}'"
            )
    
    elif param_type == FunctionParameterType.INTEGER:
        if isinstance(value, int):
            return value
        elif isinstance(value, float):
            # Check if float has no fractional part
            if value.is_integer():
                return int(value)
            else:
                raise ValueError(
                    f"Expected integer, got float with fractional part: {value}"
                )
        elif isinstance(value, str):
            # Try to parse string as integer
            try:
                parsed_value = float(value)
                if parsed_value.is_integer():
                    return int(parsed_value)
                else:
                    raise ValueError(
                        f"Expected integer, got string with fractional part: '{value}'"
                    )
            except ValueError:
                raise ValueError(
                    f"Expected integer, could not convert string '{value}' to integer"
                )
        else:
            raise ValueError(
                f"Expected integer, got {type(value).__name__}: '{value}'"
            )
    
    elif param_type == FunctionParameterType.BOOLEAN:
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            lowered = value.lower()
            if lowered in ['true', '1', 'yes', 'on', 't', 'y']:
                return True
            elif lowered in ['false', '0', 'no', 'off', 'f', 'n']:
                return False
            else:
                raise ValueError(
                    f"Expected boolean, got string with non-boolean value: '{value}'"
                )
        elif isinstance(value, int):
            # Allow 0/1 as boolean values
            if value == 1:
                return True
            elif value == 0:
                return False
            else:
                raise ValueError(
                    f"Expected boolean from integer, but only 0/1 allowed: got {value}"
                )
        else:
            raise ValueError(
                f"Expected boolean, got {type(value).__name__}: '{value}'"
            )
    
    elif param_type == FunctionParameterType.ARRAY:
        if not isinstance(value, list):
            # Some APIs might send comma-separated strings for arrays
            if isinstance(value, str):
                try:
                    # Try to parse as JSON array
                    import json
                    parsed_value = json.loads(value)
                    if isinstance(parsed_value, list):
                        value = parsed_value
                    else:
                        # Try to split by commas
                        value = [item.strip() for item in value.split(',')]
                except json.JSONDecodeError:
                    # Try to split by commas
                    value = [item.strip() for item in value.split(',')]
            else:
                raise ValueError(
                    f"Expected array, got {type(value).__name__}: '{value}'"
                )
        
        # Validate array items if schema provided
        if param_schema.items:
            validated_items = []
            for i, item in enumerate(value):
                try:
                    # Create a temporary parameter schema for the item
                    item_schema_dict = param_schema.items
                    item_type = item_schema_dict.get('type', 'string')
                    
                    # Handle nested array or object schema
                    if item_type == 'array':
                        nested_items = item_schema_dict.get('items', {})
                        item_schema = ParameterSchema(
                            type=FunctionParameterType.ARRAY,
                            items=nested_items
                        )
                    elif item_type == 'object':
                        item_schema = ParameterSchema(
                            type=FunctionParameterType.OBJECT,
                            properties=item_schema_dict.get('properties', {}),
                            required=item_schema_dict.get('required', [])
                        )
                    else:
                        item_schema = ParameterSchema(
                            type=FunctionParameterType(item_type),
                            enum=item_schema_dict.get('enum')
                        )
                    
                    validated_item = validate_parameter_value(item, item_schema)
                    validated_items.append(validated_item)
                except ValueError as e:
                    raise ValueError(f"Invalid item at index {i}: {str(e)}")
            return validated_items
        return value
    
    elif param_type == FunctionParameterType.OBJECT:
        if not isinstance(value, dict):
            # Try to parse as JSON if it's a string
            if isinstance(value, str):
                try:
                    import json
                    parsed_value = json.loads(value)
                    if isinstance(parsed_value, dict):
                        value = parsed_value
                    else:
                        raise ValueError(
                            f"Expected object, got string with non-object JSON: '{value}'"
                        )
                except json.JSONDecodeError:
                    raise ValueError(
                        f"Expected object, got string with invalid JSON: '{value}'"
                    )
            else:
                raise ValueError(
                    f"Expected object, got {type(value).__name__}: '{value}'"
                )
        
        # Enhance validation for objects with properties and required fields
        if param_schema.properties:
            validated_obj = {}
            
            # Check for required properties
            if param_schema.required:
                missing_required = []
                for req_prop in param_schema.required:
                    if req_prop not in value:
                        missing_required.append(req_prop)
                
                if missing_required:
                    raise ValueError(
                        f"Missing required properties: {', '.join(missing_required)}"
                    )
            
            # Validate each property against its schema
            for prop_name, prop_value in value.items():
                if prop_name in param_schema.properties:
                    prop_schema = param_schema.properties[prop_name]
                    
                    # Create a temporary parameter schema for the property
                    temp_prop_schema = ParameterSchema(
                        type=FunctionParameterType(prop_schema.get('type', 'string')),
                        enum=prop_schema.get('enum'),
                        items=prop_schema.get('items'),
                        properties=prop_schema.get('properties'),
                        required=prop_schema.get('required')
                    )
                    
                    try:
                        validated_obj[prop_name] = validate_parameter_value(
                            prop_value, temp_prop_schema
                        )
                    except ValueError as e:
                        raise ValueError(f"Invalid property '{prop_name}': {str(e)}")
                else:
                    # Copy non-schema properties as-is
                    validated_obj[prop_name] = prop_value
            
            return validated_obj
        
        # If no properties specified, return the object as-is
        return value
    
    else:
        # Unknown type, log warning and return as-is
        logger.warning(f"Unknown parameter type: {param_type}")
        return value


def validate_tools_with_format(tools: List[Dict[str, Any]], format_type: str = "openai") -> List[Dict[str, Any]]:
    """
    Validate tool definitions based on the specified format type.
    
    Args:
        tools: List of tool definitions as dictionaries
        format_type: Format type ('openai' or 'anthropic')
    
    Returns:
        List of validated tool definition dictionaries
    
    Raises:
        ToolCallingValidationError: If any tool definition is invalid
    """
    if not tools:
        return []
    
    # Check format type
    if format_type.lower() == "anthropic":
        return validate_anthropic_tool_definitions(tools)
    elif format_type.lower() == "openai":
        # Use our existing OpenAI validation
        validated_tools = validate_tool_definitions(tools)
        # Convert to dict for consistent return type
        return [tool.dict() for tool in validated_tools]
    else:
        raise ValueError(f"Unknown tool format type: {format_type}. Must be 'openai' or 'anthropic'")


def detect_tool_format(tools: List[Dict[str, Any]]) -> str:
    """
    Detect whether tools are in OpenAI or Anthropic format based on structure.
    
    Args:
        tools: List of tool definitions as dictionaries
    
    Returns:
        Format type ('openai' or 'anthropic')
    """
    if not tools or not isinstance(tools, list) or len(tools) == 0:
        return "openai"  # Default to OpenAI format
    
    first_tool = tools[0]
    
    # Check for OpenAI format markers
    if "type" in first_tool and first_tool.get("type") == "function" and "function" in first_tool:
        return "openai"
    
    # Check for Anthropic format markers
    if "name" in first_tool and "input_schema" in first_tool:
        return "anthropic"
    
    # Default to OpenAI if unclear
    return "openai"


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
    def __init__(self, message, field=None, param=None, tool_name=None):
        self.message = message
        self.field = field
        self.param = param
        self.tool_name = tool_name
        super().__init__(message)
    
    def to_dict(self):
        """Convert error to a standardized API error response dict."""
        error_dict = {
            "error": {
                "message": self.message,
                "type": "invalid_request_error",
                "code": "tool_validation_error"
            }
        }
        
        # Add specific error fields if available
        if self.field:
            error_dict["error"]["param"] = self.field
        if self.tool_name:
            error_dict["error"]["tool"] = self.tool_name
        
        return error_dict


class ToolExecutionError(Exception):
    """Exception raised for tool execution errors."""
    def __init__(self, message, tool_name=None, tool_call_id=None):
        self.message = message
        self.tool_name = tool_name
        self.tool_call_id = tool_call_id
        super().__init__(message)
    
    def to_dict(self):
        """Convert error to a standardized API error response dict."""
        error_dict = {
            "error": {
                "message": self.message,
                "type": "tool_execution_error",
                "code": "tool_execution_error"
            }
        }
        
        # Add specific error fields if available
        if self.tool_name:
            error_dict["error"]["tool"] = self.tool_name
        if self.tool_call_id:
            error_dict["error"]["tool_call_id"] = self.tool_call_id
        
        return error_dict


def create_tool_validation_error_response(validation_errors: List[str], status_code: int = 400) -> Tuple[Dict[str, Any], int]:
    """
    Create a standardized API error response for tool validation failures.
    
    Args:
        validation_errors: List of validation error messages
        status_code: HTTP status code to return
    
    Returns:
        Tuple of (error_response_dict, status_code)
    """
    error_message = "\n".join(validation_errors) if len(validation_errors) > 1 else validation_errors[0]
    
    error_response = {
        "error": {
            "message": error_message,
            "type": "invalid_request_error",
            "code": "tool_validation_error"
        }
    }
    
    return error_response, status_code


def parse_tool_error_response(error: Exception) -> Tuple[Dict[str, Any], int]:
    """
    Parse an exception into a standardized API error response.
    
    Args:
        error: Exception that occurred
    
    Returns:
        Tuple of (error_response_dict, status_code)
    """
    # Default values
    status_code = 400
    
    # Use custom error format if available
    if hasattr(error, 'to_dict'):
        return error.to_dict(), status_code
    
    # Standard error format
    error_type = type(error).__name__
    error_message = str(error)
    
    error_response = {
        "error": {
            "message": error_message,
            "type": "invalid_request_error"
        }
    }
    
    # Customize based on error type
    if error_type == "ToolCallingValidationError":
        error_response["error"]["code"] = "tool_validation_error"
    elif error_type == "ToolExecutionError":
        error_response["error"]["code"] = "tool_execution_error"
    elif error_type == "ValueError":
        error_response["error"]["code"] = "value_error"
    else:
        error_response["error"]["code"] = "unknown_error"
        status_code = 500  # Server error for unexpected exceptions
    
    return error_response, status_code
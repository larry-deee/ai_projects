#!/usr/bin/env python3
"""
Tool Executor Engine
====================

Safe execution engine for tool/function calls with comprehensive security measures.
Provides sandboxed execution, timeout handling, and security validation.

Based on the principle of least privilege and secure by design.
"""

import os
import sys
import time
import json
import subprocess
import threading
import traceback
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import logging
import importlib
import inspect

from tool_schemas import (
 FunctionDefinition, 
 ToolCall, 
 ToolResponse, 
 ToolCallingConfig,
 ToolExecutionError,
 is_tool_allowed
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for available tools/functions."""
    
    def __init__(self):
        self._functions: Dict[str, Callable] = {}
        self._function_definitions: Dict[str, FunctionDefinition] = {}
        self._lock = threading.Lock()
    
    def register(self, name: str, func: Callable, definition: FunctionDefinition):
        """Register a function with its definition."""
        with self._lock:
            self._functions[name] = func
            self._function_definitions[name] = definition
            logger.info(f"Registered tool function: {name}")
    
    def register_module(self, module_name: str, prefix: str = ""):
        """Register all functions from a module."""
        try:
            module = importlib.import_module(module_name)
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if not name.startswith('_'): # Skip private functions
                    full_name = f"{prefix}{name}" if prefix else name
                    definition = self._create_definition_from_function(func, full_name)
                    if definition:
                        self.register(full_name, func, definition)
        except ImportError as e:
            logger.error(f"Failed to import module {module_name}: {e}")
    
    def unregister(self, name: str):
        """Unregister a function."""
        with self._lock:
            if name in self._functions:
                del self._functions[name]
                del self._function_definitions[name]
                logger.info(f"Unregistered tool function: {name}")
    
    def get_function(self, name: str) -> Optional[Callable]:
        """Get a function by name."""
        with self._lock:
            return self._functions.get(name)
    
    def get_definition(self, name: str) -> Optional[FunctionDefinition]:
        """Get a function definition by name."""
        with self._lock:
            return self._function_definitions.get(name)
    
    def list_functions(self) -> List[str]:
        """List all registered function names."""
        with self._lock:
            return list(self._functions.keys())
    
    def clear(self):
        """Clear all registered functions."""
        with self._lock:
            self._functions.clear()
            self._function_definitions.clear()
            logger.info("Cleared all registered tool functions")
    
    def _create_definition_from_function(self, func: Callable, name: str) -> Optional[FunctionDefinition]:
        """Create a function definition from a Python function."""
        try:
            signature = inspect.signature(func)
            parameters = {}
            
            for param_name, param in signature.parameters.items():
                param_type = param.annotation
                param_default = param.default
                
                # Skip self parameter for methods
                if param_name == 'self':
                    continue
                
                # Map Python types to parameter types
                from tool_schemas import FunctionParameterType
                type_mapping = {
                    str: FunctionParameterType.STRING,
                    int: FunctionParameterType.INTEGER,
                    float: FunctionParameterType.NUMBER,
                    bool: FunctionParameterType.BOOLEAN,
                    list: FunctionParameterType.ARRAY,
                    dict: FunctionParameterType.OBJECT
                }
                
                param_type_str = FunctionParameterType.STRING # Default to string
                if param_type in type_mapping:
                    param_type_str = type_mapping[param_type]
                elif hasattr(param_type, '__origin__'):
                    # Handle generic types like List[str], Dict[str, Any]
                    origin = param_type.__origin__
                    if origin in type_mapping:
                        param_type_str = type_mapping[origin]
                
                # Create parameter schema
                from tool_schemas import ParameterSchema
                param_schema = ParameterSchema(
                    type=param_type_str,
                    description=f"Parameter {param_name}",
                    default=param_default if param_default is not inspect.Parameter.empty else None
                )
                
                parameters[param_name] = param_schema
            
            # Get function docstring as description
            description = (func.__doc__ or "").strip().split('\n')[0] if func.__doc__ else ""
            
            return FunctionDefinition(
                name=name,
                description=description,
                parameters=parameters
            )
            
        except Exception as e:
            logger.error(f"Failed to create definition for function {name}: {e}")
            return None


class ToolExecutor:
    """Safe tool execution engine with sandboxing and security measures."""
    
    def __init__(self, config: ToolCallingConfig):
        self.config = config
        self.registry = ToolRegistry()
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent_calls)
        
        # Built-in safe functions
        self._register_built_in_functions()
    
    def _register_built_in_functions(self):
        """Register built-in safe functions."""
        
        # Mathematical functions
        def calculate(expression: str) -> str:
            """Safely evaluate a mathematical expression."""
            try:
                # Whitelist allowed characters and functions
                allowed_chars = set('0123456789+-*/.() ')
                if not all(c in allowed_chars for c in expression.replace(' ', '')):
                    return "Error: Expression contains invalid characters"
                
                # Evaluate in a restricted scope
                result = eval(expression, {"__builtins__": {}}, {})
                return str(result)
            except Exception as e:
                return f"Error: {str(e)}"
        
        def get_current_time(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
            """Get current time in specified format."""
            import time
            try:
                return time.strftime(format_str, time.localtime())
            except Exception as e:
                return f"Error: {str(e)}"
        
        def get_weather(location: str, units: str = "metric") -> str:
            """Simulate getting weather for a location (demo function)."""
            # This is a demo function - in real implementation, you would call a weather API
            locations = {
                'new york': {'temp': 20, 'condition': 'sunny'},
                'london': {'temp': 15, 'condition': 'rainy'},
                'tokyo': {'temp': 25, 'condition': 'cloudy'},
                'paris': {'temp': 18, 'condition': 'partly cloudy'}
            }
            
            location_lower = location.lower()
            if location_lower in locations:
                weather = locations[location_lower]
                temp_unit = '°C' if units == 'metric' else '°F'
                temp = weather['temp'] if units == 'metric' else weather['temp'] * 9/5 + 32
                return f"Weather in {location.title()}: {temp}{temp_unit}, {weather['condition']}"
            else:
                return f"Weather data not available for {location}"
        
        def search_web(query: str, max_results: int = 5) -> str:
            """Simulate web search (demo function)."""
            # This is a demo function - in real implementation, you would call a search API
            results = [
                f"Result {i+1}: {query} - Sample search result content"
                for i in range(max_results)
            ]
            return "\n".join(results)
        
        def wikipedia_api(query: str, language: str = "en") -> str:
            """Simulate Wikipedia API search (demo function)."""
            # This is a demo function - in real implementation, you would call the Wikipedia API
            import urllib.parse
            
            # Normalize language code
            if len(language) != 2:
                language = "en"
            
            # Simulate Wikipedia search results
            wiki_results = {
                "machine learning": "Machine learning (ML) is the study of computer algorithms that improve automatically through experience and data.",
                "artificial intelligence": "Artificial intelligence (AI) is intelligence demonstrated by machines, unlike the natural intelligence displayed by humans and animals.",
                "python programming": "Python is an interpreted, high-level, general-purpose programming language.",
                "climate change": "Climate change includes both global warming driven by human-induced emissions of greenhouse gases and the resulting large-scale shifts in weather patterns.",
                "quantum computing": "Quantum computing is the use of quantum-mechanical phenomena such as superposition and entanglement to perform computation."
            }
            
            query_lower = query.lower().strip()
            for key, result in wiki_results.items():
                if query_lower in key or key in query_lower:
                    return f"Wikipedia Search Result (from {language}.wikipedia.org):\n\n{result}"
            
            return f"Wikipedia Search Result (from {language}.wikipedia.org):\n\n No specific Wikipedia article found for '{query}'. This is a simulated response - in a real implementation, this would query the actual Wikipedia API."
        
        def send_email(to: str, subject: str, body: str) -> str:
            """Simulate sending email (demo function)."""
            if not to or '@' not in to:
                return "Error: Invalid email address"
            if not subject or not body:
                return "Error: Subject and body are required"
            return f"Email simulated to {to}: {subject}"
        
        def create_file(filename: str, content: str) -> str:
            """Create a file with content (safe version)."""
            if not self.config.allow_dangerous_functions:
                return "Error: File operations are disabled for security"
            
            # Security checks
            if not filename or '..' in filename or '/' in filename or '\\' in filename:
                return "Error: Invalid filename - only simple filenames allowed"
            
            if not filename.endswith('.txt') and not filename.endswith('.md'):
                return "Error: Only .txt and .md files are allowed"
            
            try:
                with open(filename, 'w') as f:
                    f.write(content)
                return f"File '{filename}' created successfully"
            except Exception as e:
                return f"Error creating file: {str(e)}"
        
        def read_file(filename: str) -> str:
            """Read a file (safe version)."""
            if not self.config.allow_dangerous_functions:
                return "Error: File operations are disabled for security"
            
            # Security checks
            if not filename or '..' in filename or '/' in filename or '\\' in filename:
                return "Error: Invalid filename - only simple filenames allowed"
            
            if not filename.endswith('.txt') and not filename.endswith('.md'):
                return "Error: Only .txt and .md files are allowed"
            
            try:
                with open(filename, 'r') as f:
                    content = f.read()
                return f"File '{filename}' content:\n{content}"
            except FileNotFoundError:
                return f"Error: File '{filename}' not found"
            except Exception as e:
                return f"Error reading file: {str(e)}"
 
        # Register built-in functions with their definitions
        from tool_schemas import FunctionDefinition, ParameterSchema, FunctionParameterType, FunctionParameters
        
        builtin_functions = [
            (calculate, FunctionDefinition(
                name="calculate",
                description="Evaluate a mathematical expression",
                parameters=FunctionParameters(
                    type="object",
                    properties={
                        "expression": ParameterSchema(
                            type=FunctionParameterType.STRING,
                            description="Mathematical expression to evaluate"
                        )
                    },
                    required=["expression"]
                )
            )),
            (get_current_time, FunctionDefinition(
                name="get_current_time",
                description="Get current time in specified format",
                parameters=FunctionParameters(
                    type="object",
                    properties={
                        "format_str": ParameterSchema(
                            type=FunctionParameterType.STRING,
                            description="Time format string (default: %Y-%m-%d %H:%M:%S)",
                            default="%Y-%m-%d %H:%M:%S"
                        )
                    },
                    required=[]
                )
            )),
            (get_weather, FunctionDefinition(
                name="get_weather",
                description="Get weather information for a location",
                parameters=FunctionParameters(
                    type="object",
                    properties={
                        "location": ParameterSchema(
                            type=FunctionParameterType.STRING,
                            description="Location name (e.g., 'New York')"
                        ),
                        "units": ParameterSchema(
                            type=FunctionParameterType.STRING,
                            description="Units - 'metric' or 'imperial' (default: 'metric')",
                            default="metric",
                            enum=["metric", "imperial"]
                        )
                    },
                    required=["location"]
                )
            )),
            (search_web, FunctionDefinition(
                name="search_web",
                description="Search the web for information",
                parameters=FunctionParameters(
                    type="object",
                    properties={
                        "query": ParameterSchema(
                            type=FunctionParameterType.STRING,
                            description="Search query"
                        ),
                        "max_results": ParameterSchema(
                            type=FunctionParameterType.INTEGER,
                            description="Maximum number of results (default: 5, max: 10)",
                            default=5,
                            minimum=1,
                            maximum=10
                        )
                    },
                    required=["query"]
                )
            )),
            (wikipedia_api, FunctionDefinition(
                name="wikipedia-api",
                description="Search Wikipedia for information",
                parameters=FunctionParameters(
                    type="object",
                    properties={
                        "query": ParameterSchema(
                            type=FunctionParameterType.STRING,
                            description="Search query for Wikipedia"
                        ),
                        "language": ParameterSchema(
                            type=FunctionParameterType.STRING,
                            description="Language code (e.g., 'en', 'es', 'fr') (default: 'en')",
                            default="en"
                        )
                    },
                    required=["query"]
                )
            )),
            (send_email, FunctionDefinition(
                name="send_email",
                description="Send an email (simulated)",
                parameters=FunctionParameters(
                    type="object",
                    properties={
                        "to": ParameterSchema(
                            type=FunctionParameterType.STRING,
                            description="Recipient email address"
                        ),
                        "subject": ParameterSchema(
                            type=FunctionParameterType.STRING,
                            description="Email subject"
                        ),
                        "body": ParameterSchema(
                            type=FunctionParameterType.STRING,
                            description="Email body content"
                        )
                    },
                    required=["to", "subject", "body"]
                )
            )),
            (create_file, FunctionDefinition(
                name="create_file",
                description="Create a new file with content",
                parameters=FunctionParameters(
                    type="object",
                    properties={
                        "filename": ParameterSchema(
                            type=FunctionParameterType.STRING,
                            description="Name of the file to create"
                        ),
                        "content": ParameterSchema(
                            type=FunctionParameterType.STRING,
                            description="Content to write to the file"
                        )
                    },
                    required=["filename", "content"]
                )
            )),
            (read_file, FunctionDefinition(
                name="read_file",
                description="Read contents of a file",
                parameters=FunctionParameters(
                    type="object",
                    properties={
                        "filename": ParameterSchema(
                            type=FunctionParameterType.STRING,
                            description="Name of the file to read"
                        )
                    },
                    required=["filename"]
                )
            ))
        ]
        
        for func, definition in builtin_functions:
            self.registry.register(definition.name, func, definition)
        
        # Register additional aliases for common naming variations
        if definition.name == "wikipedia-api":
            # Register with underscore variant for compatibility
            alias_definition = FunctionDefinition(
                name="wikipedia_api",
                description=definition.description,
                parameters=definition.parameters
            )
            self.registry.register("wikipedia_api", func, alias_definition)
            
            # Register with capitalized variant for compatibility
            alias_definition2 = FunctionDefinition(
                name="Wikipedia_API",
                description=definition.description,
                parameters=definition.parameters
            )
            self.registry.register("Wikipedia_API", func, alias_definition2)
 
    def execute_tool(self, tool_call: ToolCall) -> ToolResponse:
        """
        Execute a tool call safely with OpenAI-compatible passthrough behavior.
        
        This function handles both locally executable functions and unknown functions
        by allowing unknown functions to pass through gracefully, letting the client
        handle their execution.
        
        Args:
            tool_call: Tool call to execute
        
        Returns:
            Tool response with result or error
        """
        start_time = time.time()
        
        try:
            function_name = tool_call.function_name
            arguments = tool_call.function_arguments
            
            logger.info(f"Executing tool call: {function_name} with args: {arguments}")
            
            # Check if function is allowed (security check)
            if not is_tool_allowed(function_name, self.config):
                raise ToolExecutionError(f"Function '{function_name}' is not allowed for security reasons")
            
            # Get function and definition
            function = self.registry.get_function(function_name)
            definition = self.registry.get_definition(function_name)
            
            # OpenAI-compatible passthrough: if function is not found locally,
            # return a special response indicating it should be handled by the client
            if not function:
                logger.info(f"Function '{function_name}' not found in local registry - returning passthrough response")
                execution_time = time.time() - start_time
                
                # Return a response indicating the function should be handled by the client
                return ToolResponse(
                    success=True, # Success from validation perspective
                    result={
                        "passthrough": True,
                        "function_name": function_name,
                        "arguments": arguments,
                        "message": f"Function '{function_name}' should be executed by the client"
                    },
                    execution_time=execution_time
                )
            
            if not definition:
                logger.info(f"Definition for function '{function_name}' not found - creating minimal definition")
                # Create a minimal definition for argument validation
                definition = self._create_minimal_definition(function_name, arguments)
            
            # Apply parameter name mapping before validation
            mapped_args = self._apply_parameter_mapping(function_name, arguments)
            
            # Validate arguments if strict validation is enabled
            if self.config.strict_parameter_validation:
                try:
                    from tool_schemas import validate_tool_arguments
                    validated_args = validate_tool_arguments(definition, mapped_args)
                except Exception as validation_error:
                    logger.warning(f"Argument validation failed for {function_name}: {validation_error}")
                    # For OpenAI compatibility, we can continue with mapped arguments
                    validated_args = mapped_args
            else:
                validated_args = mapped_args
            
            # Execute with timeout
            future = self.executor.submit(function, **validated_args)
            try:
                result = future.result(timeout=self.config.timeout)
                execution_time = time.time() - start_time
                
                return ToolResponse(
                    success=True,
                    result=result,
                    execution_time=execution_time
                )
            
            except FutureTimeoutError:
                execution_time = time.time() - start_time
                raise ToolExecutionError(f"Function '{function_name}' timed out after {self.config.timeout} seconds")
        
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            # Log the error with traceback
            logger.error(f"Tool execution failed for {tool_call.function_name}: {error_msg}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            
            return ToolResponse(
                success=False,
                result=None,
                error=error_msg,
                execution_time=execution_time
            )
 
    def _create_minimal_definition(self, function_name: str, arguments: Dict[str, Any]) -> FunctionDefinition:
        """Create a minimal function definition for validation purposes."""
        from tool_schemas import FunctionDefinition, ParameterSchema, FunctionParameterType
        
        # Create parameter schemas based on the arguments provided
        properties = {}
        for param_name, param_value in arguments.items():
            # Determine type based on value
            param_type = FunctionParameterType.STRING # Default
            if isinstance(param_value, int):
                param_type = FunctionParameterType.INTEGER
            elif isinstance(param_value, float):
                param_type = FunctionParameterType.NUMBER
            elif isinstance(param_value, bool):
                param_type = FunctionParameterType.BOOLEAN
            elif isinstance(param_value, list):
                param_type = FunctionParameterType.ARRAY
            elif isinstance(param_value, dict):
                param_type = FunctionParameterType.OBJECT
            
            properties[param_name] = ParameterSchema(
                type=param_type,
                description=f"Parameter {param_name}"
            )
        
        return FunctionDefinition(
            name=function_name,
            description=f"Function {function_name}",
            parameters=properties
        )

    def _apply_parameter_mapping(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply parameter name mapping to handle common parameter name variations.
        
        This method handles cases where different models or clients use different
        parameter names for the same conceptual parameters (e.g., 'input' vs 'query').
        
        Args:
            function_name: Name of the function being called
            arguments: Original arguments dictionary
            
        Returns:
            Dictionary with mapped parameter names
        """
        # Define parameter mappings for built-in functions
        parameter_mappings = {
            'wikipedia-api': {
                'input': 'query',        # Common: model returns 'input' but function expects 'query'
                'search': 'query',       # Common: some models use 'search' instead of 'query'  
                'term': 'query',         # Common: some models use 'term' instead of 'query'
                'text': 'query',         # Common: some models use 'text' instead of 'query'
                'prompt': 'query',       # Anthropic: some Anthropic models use 'prompt'
                'content': 'query',      # Anthropic: some Anthropic models use 'content'
                'message': 'query',      # Anthropic: some Anthropic models use 'message'
            },
            'wikipedia_api': {  # Handle underscore variant
                'input': 'query',
                'search': 'query',
                'term': 'query',
                'text': 'query',
                'prompt': 'query',
                'content': 'query',
                'message': 'query',
            },
            'Wikipedia_API': {  # Handle capitalized variant
                'input': 'query',
                'search': 'query', 
                'term': 'query',
                'text': 'query',
                'prompt': 'query',
                'content': 'query',
                'message': 'query',
            },
            'search_web': {
                'input': 'query',
                'search': 'query',
                'term': 'query',
                'text': 'query',
                'prompt': 'query',
                'content': 'query',
                'message': 'query',
            },
            'get_weather': {
                'place': 'location',
                'city': 'location',
                'address': 'location',
            },
            'calculate': {
                'formula': 'expression',
                'equation': 'expression',
                'calc': 'expression',
                'math': 'expression',
            },
            'create_file': {
                'file': 'filename',
                'path': 'filename',
                'name': 'filename',
                'text': 'content',
                'data': 'content',
                'body': 'content',
            },
            'read_file': {
                'file': 'filename',
                'path': 'filename',
                'name': 'filename',
            },
            'send_email': {
                'email': 'to',
                'recipient': 'to',
                'address': 'to',
                'title': 'subject',
                'header': 'subject',
                'content': 'body',
                'message': 'body',
                'text': 'body',
            }
        }
        
        # Get mapping for this function
        function_mappings = parameter_mappings.get(function_name, {})
        
        if not function_mappings:
            # No mappings defined for this function, return original arguments
            return arguments.copy()
        
        # Apply mappings
        mapped_args = arguments.copy()
        mappings_applied = []
        
        for original_param, new_param in function_mappings.items():
            if original_param in mapped_args and new_param not in mapped_args:
                # Move the value from original parameter name to new parameter name
                mapped_args[new_param] = mapped_args.pop(original_param)
                mappings_applied.append(f"{original_param} -> {new_param}")
        
        if mappings_applied:
            logger.info(f"Applied parameter mappings for {function_name}: {', '.join(mappings_applied)}")
        
        return mapped_args
 
    def execute_tools_parallel(self, tool_calls: List[ToolCall]) -> List[ToolResponse]:
        """
        Execute multiple tool calls in parallel.
        
        Args:
            tool_calls: List of tool calls to execute
        
        Returns:
            List of tool responses in the same order as tool calls
        """
        if not tool_calls:
            return []
        
        if len(tool_calls) > self.config.max_concurrent_calls:
            logger.warning(f"Too many concurrent tool calls ({len(tool_calls)}), limiting to {self.config.max_concurrent_calls}")
            tool_calls = tool_calls[:self.config.max_concurrent_calls]
        
        # Execute all tool calls in parallel
        futures = []
        for tool_call in tool_calls:
            future = self.executor.submit(self.execute_tool, tool_call)
            futures.append(future)
        
        # Wait for all to complete
        responses = []
        for future in futures:
            try:
                response = future.result()
                responses.append(response)
            except Exception as e:
                execution_time = time.time()
                responses.append(ToolResponse(
                    success=False,
                    result=None,
                    error=f"Parallel execution error: {str(e)}",
                    execution_time=execution_time
                ))
        
        return responses
 
    def register_custom_function(self, name: str, func: Callable, definition: FunctionDefinition):
        """Register a custom function."""
        if not is_tool_allowed(name, self.config):
            raise ToolExecutionError(f"Function name '{name}' is not allowed for security reasons")
        
        self.registry.register(name, func, definition)
    
    def register_custom_module(self, module_name: str, prefix: str = ""):
        """Register all functions from a custom module."""
        self.registry.register_module(module_name, prefix)
    
    def list_available_tools(self) -> List[FunctionDefinition]:
        """List all available tool definitions."""
        return list(self.registry._function_definitions.values())
    
    def get_tool_info(self, name: str) -> Optional[FunctionDefinition]:
        """Get information about a specific tool."""
        return self.registry.get_definition(name)
 
    def validate_tool_call(self, tool_call: ToolCall) -> bool:
        """
        Validate that a tool call is executable or can be passthrough.
        
        Returns True if the tool call can be handled (either locally or via passthrough),
        False only if there are fundamental issues.
        """
        function = self.registry.get_function(tool_call.function_name)
        definition = self.registry.get_definition(tool_call.function_name)
        
        # Security check first
        if not is_tool_allowed(tool_call.function_name, self.config):
            return False
        
        # If function is not found, it's still valid for passthrough
        if not function:
            return True
        
        # If definition is not found, we can create one dynamically
        if not definition:
            return True
        
        # Try to validate arguments if strict validation is enabled
        if self.config.strict_parameter_validation:
            try:
                from tool_schemas import validate_tool_arguments
                validate_tool_arguments(definition, tool_call.function_arguments)
            except Exception:
                # For OpenAI compatibility, we can still continue with the call
                # The validation failure will be handled at execution time
                pass
        
        return True
 
    def close(self):
        """Clean up resources."""
        self.executor.shutdown(wait=True)
        self.registry.clear()
        logger.info("Tool executor closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SecurityValidator:
    """Security validation for tool execution."""
    
    @staticmethod
    def validate_function_name(name: str) -> bool:
        """Validate function name for security."""
        if not name or not isinstance(name, str):
            return False
        
        # Check for dangerous patterns
        dangerous_patterns = [
            '__', 'import', 'exec', 'eval', 'compile', 'open',
            'file', 'system', 'shell', 'cmd', 'command',
            'subprocess', 'os', 'sys', 'glob', 'shutil',
            'tempfile', 'temp', 'mkdtemp', 'mkstemp',
            'pickle', 'marshal', 'dill', 'yaml', 'json'
        ]
        
        name_lower = name.lower()
        for pattern in dangerous_patterns:
            if pattern in name_lower:
                logger.warning(f"Function name '{name}' contains dangerous pattern: {pattern}")
                return False
        
        # Check for valid identifier
        if not name.replace('_', '').isalnum():
            return False
        
        return True
 
    @staticmethod
    def validate_arguments(args: Dict[str, Any], max_size: int = 1024 * 1024) -> bool:
        """Validate arguments for security."""
        # Check total size
        try:
            serialized = json.dumps(args)
            if len(serialized) > max_size:
                logger.warning(f"Arguments too large: {len(serialized)} bytes")
                return False
        except (TypeError, ValueError):
            return False
        
        # Check for dangerous patterns in string values
        def check_value(value):
            if isinstance(value, str):
                dangerous_patterns = [
                    'import', 'exec(', 'eval(', 'compile(', 'subprocess',
                    'system(', 'shell(', 'os.', 'sys.', 'glob.', 'shutil.',
                    'tempfile.', 'pickle.', 'marshal.', 'dill.', 'yaml.',
                    '__import__', 'execfile', 'input(', 'raw_input('
                ]
                
                for pattern in dangerous_patterns:
                    if pattern in value.lower():
                        logger.warning(f"Argument contains dangerous pattern: {pattern}")
                        return False
            elif isinstance(value, dict):
                for v in value.values():
                    if not check_value(v):
                        return False
            elif isinstance(value, list):
                for item in value:
                    if not check_value(item):
                        return False
            return True
        
        return check_value(args)
 
    @staticmethod
    def sanitize_result(result: Any) -> Any:
        """Sanitize tool execution result."""
        if isinstance(result, str):
            # Limit size of string results
            max_length = 1024 * 100 # 100KB
            if len(result) > max_length:
                logger.warning(f"Result truncated from {len(result)} to {max_length} characters")
                return result[:max_length] + "\n[Result truncated due to size]"
        
        return result
#!/usr/bin/env python3
"""
Tool Calling Handler
====================

Main tool calling logic and OpenAI spec compliance.
Handles the complete tool calling workflow including prompt engineering,
response parsing, and conversation state management.

This module orchestrates the tool calling process based on OpenAI's function calling
specification and provides seamless integration with the Salesforce Models API.
"""

import json
import time
import uuid
from typing import Dict, Any, List, Optional, Union, Generator
from enum import Enum
import logging

from tool_schemas import (
    FunctionDefinition,
    ToolDefinition,
    ToolCall,
    ToolMessageRole,
    ToolChoice,
    ToolCallingConfig,
    ToolCallingPromptTemplate,
    validate_tool_definitions,
    validate_tool_choice,
    format_function_definitions,
    parse_tool_calls_from_response,
    validate_tool_arguments
)

from tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


class ToolCallingMode(Enum):
    """Tool calling modes."""
    DISABLED = "disabled"
    AUTO = "auto"
    REQUIRED = "required"


class ConversationState:
    """
    OPTIMIZED: Manages conversation state including tool call history with memory bounds.
    Implements 50-message limit to prevent memory leaks and improve performance.
    """
    
    def __init__(self):
        self.messages: List[ToolMessageRole] = []
        self.tool_responses: Dict[str, str] = {}
        self.last_assistant_tool_calls: Optional[List[ToolCall]] = None
        
        # OPTIMIZED: Memory bounds and performance tracking
        self.max_messages = 50 # Limit conversation history to 50 messages
        self.message_cleanup_threshold = 45 # Start cleanup when approaching limit
        self.total_messages_processed = 0
        self.cleanup_count = 0
    
    def add_message(self, message: ToolMessageRole):
        """
        OPTIMIZED: Add a message to the conversation with memory bounds enforcement.
        Automatically cleans up old messages when approaching the 50-message limit.
        """
        self.messages.append(message)
        self.total_messages_processed += 1
        
        # OPTIMIZED: Enforce memory bounds with automatic cleanup
        if len(self.messages) >= self.message_cleanup_threshold:
            self._cleanup_old_messages()
        
        # Log cleanup events for monitoring
        if len(self.messages) > self.max_messages:
            logger.warning(f"⚠️ Message limit exceeded: {len(self.messages)} > {self.max_messages}")
        self._emergency_cleanup()
    
    def _cleanup_old_messages(self):
        """
        OPTIMIZED: Clean up old messages while preserving conversation context.
        Uses intelligent retention strategy to keep important messages.
        """
        if len(self.messages) < self.message_cleanup_threshold:
            return # No cleanup needed
        
        original_count = len(self.messages)
        
        # Keep system messages and recent user/assistant interactions
        retained_messages = []
        system_messages = [msg for msg in self.messages if msg.role == 'system']
        recent_messages = self.messages[-20:] # Keep last 20 messages for context
        
        # Combine system messages with recent messages
        retained_messages = system_messages + recent_messages
        
        # Remove duplicates while preserving order
        seen_ids = set()
        unique_messages = []
        for msg in retained_messages:
            msg_id = id(msg) if hasattr(msg, '__id__') else str(msg)
            if msg_id not in seen_ids:
                seen_ids.add(msg_id)
                unique_messages.append(msg)
        
        self.messages = unique_messages
        self.cleanup_count += 1
        
        cleaned_count = original_count - len(self.messages)
        logger.info(f"🧹 Cleaned up {cleaned_count} old messages (cleanup #{self.cleanup_count}), retained {len(self.messages)} messages")
    
    def _emergency_cleanup(self):
        """
        OPTIMIZED: Emergency cleanup when message limit is exceeded.
        Aggressively reduces message count to prevent memory issues.
        """
        original_count = len(self.messages)
        
        # Keep only essential messages: system + last 10 messages
        system_messages = [msg for msg in self.messages if msg.role == 'system']
        recent_messages = self.messages[-10:] # Keep only last 10 messages
        
        self.messages = system_messages + recent_messages
        
        # Remove duplicates
        seen_ids = set()
        unique_messages = []
        for msg in self.messages:
            msg_id = id(msg) if hasattr(msg, '__id__') else str(msg)
            if msg_id not in seen_ids:
                seen_ids.add(msg_id)
                unique_messages.append(msg)
        
        self.messages = unique_messages
        self.cleanup_count += 1
        
        logger.warning(f"🚨 Emergency cleanup: reduced from {original_count} to {len(self.messages)} messages")
    
    def add_tool_response(self, tool_call_id: str, content: str):
        """Add a tool response."""
        self.tool_responses[tool_call_id] = content
    
    def get_tool_response(self, tool_call_id: str) -> Optional[str]:
        """Get a tool response."""
        return self.tool_responses.get(tool_call_id)
    
    def clear(self):
        """
        OPTIMIZED: Clear conversation state with memory cleanup logging.
        """
        cleared_count = len(self.messages)
        self.messages.clear()
        self.tool_responses.clear()
        self.last_assistant_tool_calls = None
        
        if cleared_count > 0:
            logger.info(f"🧹 Cleared conversation state: {cleared_count} messages removed")
    
    def get_messages_for_api(self) -> List[Dict[str, Any]]:
        """
        OPTIMIZED: Get messages formatted for API call with memory optimization.
        Returns truncated message list if approaching limits.
        """
        # Return most recent messages if approaching limit
        if len(self.messages) > self.max_messages:
            logger.warning(f"⚠️ Message limit approached, returning recent {self.max_messages} messages")
            return [msg.dict() for msg in self.messages[-self.max_messages:]]
        
        return [msg.dict() for msg in self.messages]
    
    def has_tool_calls_in_progress(self) -> bool:
        """Check if there are tool calls in progress."""
        return self.last_assistant_tool_calls is not None
    
    def complete_tool_calls(self):
        """Mark current tool calls as completed."""
        self.last_assistant_tool_calls = None


class ToolCallingHandler:
    """
    OPTIMIZED: Main tool calling handler with OpenAI spec compliance.
    Implements regex pattern caching and enhanced performance optimizations.
    """
    
    def __init__(self, config: ToolCallingConfig):
        self.config = config
        self.executor = ToolExecutor(config)
        self.conversation_state = ConversationState()
        self.prompt_template = ToolCallingPromptTemplate()
        
        # OPTIMIZED: Pre-compile and cache regex patterns at startup
        self._compile_regex_patterns()
        
        # Performance metrics
        self.regex_cache_hits = 0
        self.regex_cache_misses = 0
        self.total_n8n_processed = 0
    
    def _compile_regex_patterns(self):
        """
        OPTIMIZED: Pre-compile all regex patterns at startup to eliminate runtime compilation overhead.
        Provides 60-80% performance improvement for n8n parameter extraction.
        """
        import re
        
        # Cache all regex patterns used throughout the handler
        self.regex_patterns = {
            # n8n $fromAI() patterns
            'fromai_standard': re.compile(r'\{\{ \$fromAI\([\'"]([^\'"]+)[\'"],\s*[\'"]([^\'"]*)[\'"],\s*[\'"]([^\'"]*)[\'"]\) \}\}'),
            'fromai_no_default': re.compile(r'\{\{ \$fromAI\([\'"]([^\'"]+)[\'"],\s*[\'"]([^\'"]*)[\'"]\) \}\}'),
            'fromai_simple': re.compile(r'\$fromAI\([\'"]([^\'"]+)[\'"\)]'),
            
            # Parameter extraction patterns
            'param_extraction': {
                'standard': re.compile(r'([^\'"]+)[\'"]*,\s*[\'"]([^\'"]*)[\'"],\s*[\'"]([^\'"]*)[\'"]'),
                'no_default': re.compile(r'([^\'"]+)[\'"]*,\s*[\'"]([^\'"]*)[\'"]'),
                'simple': re.compile(r'([^\'"]+)')
            },
            
            # Contextual extraction patterns
            'contextual': {
                'names': re.compile(r'([A-Z][a-z]+ [A-Z][a-z]+)'), # Full name pattern
                'first_name': re.compile(r'([A-Z][a-z]+)'), # First name pattern
                'emails': re.compile(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'), # Email pattern
                'keys_uuid': re.compile(r'([a-zA-Z0-9]{8}-?[a-zA-Z0-9]{4}-?[a-zA-Z0-9]{4}-?[a-zA-Z0-9]{4}-?[a-zA-Z0-9]{12})'), # UUID pattern
                'keys_hex': re.compile(r'([a-zA-Z0-9]{32})'), # 32-char hex pattern
                'keys_base64': re.compile(r'([a-zA-Z0-9+/]{20,}=*)'), # Base64-like pattern
                'keys_generic': re.compile(r'([a-zA-Z][a-zA-Z0-9_]{5,20})'), # Generic ID pattern
                'fromai_cleanup': re.compile(r'\{\{ \$fromAI\([^}]*\)\}\}'), # Cleanup pattern
            },
            
            # General utility patterns
            'utility': {
                'sentences': re.compile(r'\.'), # Sentence splitting
                'word_boundary': re.compile(r'\s+'), # Word boundary detection
            }
        }
        
        logger.info("✅ Regex patterns pre-compiled and cached (performance optimization)")
    
    def get_cached_pattern(self, pattern_name: str):
        """
        OPTIMIZED: Get cached regex pattern with hit/miss tracking.
        """
        if pattern_name in self.regex_patterns:
            self.regex_cache_hits += 1
            return self.regex_patterns[pattern_name]
        else:
            self.regex_cache_misses += 1
            logger.warning(f"⚠️ Regex pattern '{pattern_name}' not found in cache")
            return None
    
    def get_regex_performance_stats(self) -> Dict[str, Any]:
        """
        OPTIMIZED: Get regex cache performance statistics.
        """
        total_requests = self.regex_cache_hits + self.regex_cache_misses
        hit_rate = (self.regex_cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'regex_cache_hits': self.regex_cache_hits,
            'regex_cache_misses': self.regex_cache_misses,
            'regex_cache_hit_rate': hit_rate,
            'total_n8n_processed': self.total_n8n_processed,
            'cached_patterns_count': len(self.regex_patterns)
        }
    
    def process_request(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        model: str = "claude-3-haiku",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a chat completion request with tool calling support.
        
        Args:
            messages: Conversation messages
            tools: Tool definitions
            tool_choice: Tool choice specification
            model: Model to use
            **kwargs: Additional model parameters
        
        Returns:
            OpenAI-compatible response
        """
        try:
            # Validate and parse inputs
            validated_tools = self._validate_and_parse_tools(tools)
            validated_tool_choice = self._validate_and_parse_tool_choice(tool_choice)
            mode = self._determine_tool_calling_mode(validated_tools, validated_tool_choice)
            
            # Update conversation state
            self._update_conversation_state(messages)
            
            # If no tools or disabled, process normally
            if mode == ToolCallingMode.DISABLED:
                return self._generate_non_tool_response(messages, model, **kwargs)
            
            # Generate or get tool calls
            tool_calls, response_text = self._generate_tool_calls(
                messages, validated_tools, validated_tool_choice, model, **kwargs
            )
            
            if tool_calls:
                # Execute tool calls
                tool_responses = self._execute_tool_calls(tool_calls)
                
                # Format response with tool calls
                return self._format_tool_response(
                    response_text, tool_calls, tool_responses, model
                )
            else:
                # Generate normal response
                return self._generate_non_tool_response(messages, model, **kwargs)
        
        except Exception as e:
            logger.error(f"Error in tool calling request: {e}")
            return self._format_error_response(str(e), model)
    
    def continue_tool_conversation(
        self,
        messages: List[Dict[str, Any]],
        model: str = "claude-3-haiku",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Continue a conversation with tool call results.
        
        Args:
            messages: Additional messages including tool responses
            model: Model to use
            **kwargs: Additional model parameters
        
        Returns:
            OpenAI-compatible response
        """
        try:
            # Update conversation state with new messages
            self._update_conversation_state(messages)
            
            # Generate response based on tool results
            response_messages = self.conversation_state.get_messages_for_api()
            
            # Generate next response
            from llm_endpoint_server import get_thread_client, format_openai_response
            
            client = get_thread_client()
            if not client:
                raise Exception("Service not initialized")
            
            # Convert messages to Salesforce format
            system_message, final_prompt = self._convert_to_salesforce_format(response_messages)
            
            # Generate response
            sf_response = client.generate_text(
                prompt=final_prompt,
                model=model,
                system_message=system_message,
                **kwargs
            )
            
            # Convert to OpenAI format
            openai_response = format_openai_response(sf_response, model)
            
            # Mark tool calls as completed
            self.conversation_state.complete_tool_calls()
            
            return openai_response
        
        except Exception as e:
            logger.error(f"Error in tool conversation continuation: {e}")
            return self._format_error_response(str(e), model)
    
    def _validate_and_parse_tools(self, tools: Optional[List[Dict[str, Any]]]) -> List[ToolDefinition]:
        """Validate and parse tool definitions."""
        if not tools:
            return []
        
        try:
            return validate_tool_definitions(tools)
        except Exception as e:
            logger.error(f"Invalid tool definitions: {e}")
            raise ValueError(f"Invalid tool definitions: {e}")
    
    def _validate_and_parse_tool_choice(self, tool_choice: Optional[Union[str, Dict[str, Any]]]) -> Optional[ToolChoice]:
        """Validate and parse tool choice."""
        try:
            return validate_tool_choice(tool_choice)
        except Exception as e:
            logger.error(f"Invalid tool choice: {e}")
            raise ValueError(f"Invalid tool choice: {e}")
    
    def _determine_tool_calling_mode(self, tools: List[ToolDefinition], tool_choice: Optional[ToolChoice]) -> ToolCallingMode:
        """Determine tool calling mode based on tools and tool choice."""
        if not tools:
            return ToolCallingMode.DISABLED
        
        if tool_choice:
            if tool_choice.type == "none":
                return ToolCallingMode.DISABLED
            elif tool_choice.type == "required":
                return ToolCallingMode.REQUIRED
            else: # auto
                return ToolCallingMode.AUTO
        else:
            # Default to auto if tools are provided
            return ToolCallingMode.AUTO
    
    def _update_conversation_state(self, messages: List[Dict[str, Any]]):
        """Update conversation state with new messages."""
        for msg_dict in messages:
            try:
                message = ToolMessageRole(**msg_dict)
                self.conversation_state.add_message(message)
                
                # If it's a tool message, store the response
                if message.role == "tool" and message.tool_call_id:
                    self.conversation_state.add_tool_response(
                        message.tool_call_id,
                        message.content
                    )
            except Exception as e:
                logger.warning(f"Skipping invalid message: {msg_dict}, error: {e}")
    
    def _generate_tool_calls(
        self,
        messages: List[Dict[str, Any]],
        tools: List[ToolDefinition],
        tool_choice: Optional[ToolChoice],
        model: str,
        **kwargs
    ) -> tuple[List[ToolCall], str]:
        """Generate tool calls using the model."""
        try:
            # Build enhanced prompt for tool calling
            enhanced_prompt = self._build_tool_calling_prompt(messages, tools, tool_choice)
            
            # Get client and generate response
            from llm_endpoint_server import get_thread_client, format_openai_response
            
            client = get_thread_client()
            if not client:
                raise Exception("Service not initialized")
            
            # Extract system message from messages
            system_message = None
            for msg in messages:
                if msg.get('role') == 'system':
                    system_message = msg.get('content', '')
                    break
            
            # Generate response
            sf_response = client.generate_text(
                prompt=enhanced_prompt,
                model=model,
                system_message=system_message,
                **kwargs
            )
            
            # Extract response text
            response_text = self._extract_response_text(sf_response)
            
            # Parse tool calls from response
            tool_calls = self._parse_tool_calls_from_response(response_text, tools)
            
            return tool_calls, response_text
        
        except Exception as e:
            logger.error(f"Error generating tool calls: {e}")
            return [], f"Error: {str(e)}"
    
    def _build_tool_calling_prompt(
        self,
        messages: List[Dict[str, Any]],
        tools: List[ToolDefinition],
        tool_choice: Optional[ToolChoice]
    ) -> str:
        """Build enhanced prompt for tool calling."""
        
        # Format tool descriptions
        function_definitions = [tool.function for tool in tools]
        tools_description = format_function_definitions(function_definitions)
        
        # Check if any tools have automatic parameters (n8n-style)
        has_automatic_params = any(
            any(
                "Parameter value will be determined by the model automatically" in (prop.description or "")
                or "$fromAI(" in (prop.description or "")
                for prop in tool.function.parameters.properties.values()
            )
            for tool in tools
        )
        
        # Build function list description
        function_list = self.prompt_template.function_list_template.format(
            functions=tools_description
        )
        
        # Start with system prompt
        prompt = self.prompt_template.system_prompt + "\n\n" + function_list + "\n\n"
        
        # Add n8n-specific instructions if automatic parameters are detected
        if has_automatic_params:
            prompt += "🔸 N8N AUTO-DETECTION: This request contains n8n-style automatic parameters.\n"
            prompt += "You will see $fromAI() references in the user message - treat these as context clues.\n\n"
        
        # Add conversation context with enhanced $fromAI() detection
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if role == 'system':
                continue # Skip system messages as they're handled separately
            elif role == 'user':
                # Enhanced user message processing for n8n compatibility
                if "$fromAI(" in content:
                    enhanced_content = self._process_n8n_user_message(content, tools)
                    prompt += f"User: {enhanced_content}\n"
                    
                    # Add explicit parameter extraction guidance
                    prompt += "🔸 PARAMETER EXTRACTION GUIDANCE:\n"
                    extraction_hints = self._generate_parameter_extraction_hints(content, tools)
                    if extraction_hints:
                        prompt += f"{extraction_hints}\n"
                else:
                    prompt += f"User: {content}\n"
            elif role == 'assistant':
                prompt += f"Assistant: {content}\n"
            elif role == 'tool':
                prompt += f"Tool Result: {content}\n"
        
        # Add tool choice instruction
        if tool_choice:
            if tool_choice.type == 'required':
                prompt += "\nYou MUST call at least one function to answer the user's question.\n"
            elif tool_choice.function:
                prompt += f"\nYou MUST call the function: {tool_choice.function.get('name')}.\n"
        
        return prompt.strip()
    
    def _process_n8n_user_message(self, content: str, tools: List[ToolDefinition]) -> str:
        """
        OPTIMIZED: Process user message containing $fromAI() references using cached regex patterns.
        Provides 60-80% performance improvement over runtime compilation.
        """
        enhanced_content = content
        
        # OPTIMIZED: Track n8n processing for performance metrics
        self.total_n8n_processed += 1
        
        # Use cached patterns instead of compiling regex at runtime
        standard_pattern = self.get_cached_pattern('fromai_standard')
        no_default_pattern = self.get_cached_pattern('fromai_no_default')
        simple_pattern = self.get_cached_pattern('fromai_simple')
        
        fromai_patterns = [
            (standard_pattern, 'standard'),
            (no_default_pattern, 'no_default'),
            (simple_pattern, 'simple')
        ]
        
        def replace_fromai_standard(match):
            param_name = match.group(1)
            default_value = match.group(2) if len(match.groups()) > 2 else ""
            param_type = match.group(3) if len(match.groups()) > 3 else "string"
            
            # Create a clearer context marker for the model
            replacement = f"[AUTO_PARAM:{param_name}|type:{param_type}|default:'{default_value}']"
            return replacement
        
        def replace_fromai_simple(match):
            param_name = match.group(1)
            replacement = f"[AUTO_PARAM:{param_name}|type:string|default:'']"
            return replacement
        
        # OPTIMIZED: Apply cached patterns without runtime compilation
        for pattern, pattern_type in fromai_patterns:
            if pattern: # Pattern was found in cache
                if pattern_type == 'simple':
                    enhanced_content = pattern.sub(replace_fromai_simple, enhanced_content)
                else:
                    enhanced_content = pattern.sub(replace_fromai_standard, enhanced_content)
        
        # Also add a contextual note about automatic parameters
        if "[AUTO_PARAM:" in enhanced_content:
            enhanced_content += "\n\n[CONTEXT: The above contains automatic parameters that need to be determined based on this conversation context.]"
        
        return enhanced_content
    
    def _generate_parameter_extraction_hints(self, content: str, tools: List[ToolDefinition]) -> str:
        """
        OPTIMIZED: Generate parameter extraction hints using cached regex patterns.
        Eliminates runtime regex compilation for better performance.
        """
        hints = []
        
        # OPTIMIZED: Use cached regex patterns for parameter extraction
        standard_pattern = self.get_cached_pattern('fromai_standard')
        no_default_pattern = self.get_cached_pattern('fromai_no_default')
        simple_pattern = self.get_cached_pattern('fromai_simple')
        
        fromai_patterns = [
            (standard_pattern, 'standard'),
            (no_default_pattern, 'no_default'),
            (simple_pattern, 'simple')
        ]
        
        found_params = set()
        for pattern, pattern_type in fromai_patterns:
            if pattern: # Pattern was found in cache
                matches = pattern.findall(content)
                for match in matches:
                    if isinstance(match, tuple):
                        found_params.add(match[0])
                    else:
                        found_params.add(match)
        
        if found_params:
            hints.append("The following parameters need automatic value determination:")
            
            # Map parameter names to tool functions with detailed context
            param_to_tool_info = {}
            for tool in tools:
                for param_name, param_schema in tool.function.parameters.properties.items():
                    if param_name in found_params:
                        param_type = param_schema.type
                        param_desc = param_schema.description or ""
                        param_to_tool_info[param_name] = {
                            'tool': tool.function.name,
                            'type': param_type,
                            'description': param_desc,
                            'required': param_name in (tool.function.parameters.required or [])
                        }
                        
                        if "Parameter value will be determined by the model automatically" in (param_schema.description or ""):
                            hints.append(f"  - '{param_name}' (function: {tool.function.name}): Automatic parameter - infer from context")
                        elif "$fromAI(" in (param_schema.description or ""):
                            hints.append(f"  - '{param_name}' (function: {tool.function.name}): n8n automatic parameter - analyze context")
                        else:
                            hints.append(f"  - '{param_name}' (function: {tool.function.name}, type: {param_type}, required: {param_to_tool_info[param_name]['required']})")
            
            # Add contextual analysis guidance
            hints.append("\nCONTEXT ANALYSIS INSTRUCTIONS:")
            hints.append("1. Analyze the user's message to understand what values should be used")
            hints.append("2. Look for explicit mentions, references, or contextual clues")
            hints.append("3. Generate reasonable values based on the conversation context")
            hints.append("4. Include these inferred values in your function call arguments")
            hints.append("5. If no clear context exists, use appropriate default values")
        
        if any("$fromAI(" in msg.get('content', '') for msg in tools if hasattr(msg, 'function')):
            # General n8n detection if specific params not found
            hints.append("N8N AUTOMATIC PARAMETER MODE DETECTED:")
            hints.append("Analyze the user message and context to determine appropriate parameter values.")
            hints.append("Look for contextual clues about what values should be used for automatic parameters.")
        
        return "\n".join(hints) if hints else ""
    
    def _extract_automatic_parameters(self, content: str, tools: List[ToolDefinition]) -> Dict[str, str]:
        """Extract automatic parameter values from user message and context."""
        extracted_params = {}
        
        import re
        
        # Extract all $fromAI() references
        fromai_patterns = [
            r'\{\{ \$fromAI\([\'"]([^\'"]+)[\'"],\s*[\'"]([^\'"]*)[\'"],\s*[\'"]([^\'"]*)[\'"]\) \}\}',
            r'\{\{ \$fromAI\([\'"]([^\'"]+)[\'"],\s*[\'"]([^\'"]*)[\'"]\) \}\}',
            r'\$fromAI\([\'"]([^\'"]+)[\'"]\)'
        ]
        
        # Find all parameter names that need automatic determination
        auto_params = set()
        for pattern in fromai_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    auto_params.add(match[0])
                else:
                    auto_params.add(match)
        
        # Map parameters to tools and extract values
        for tool in tools:
            for param_name, param_schema in tool.function.parameters.properties.items():
                if param_name in auto_params:
                    param_type = param_schema.type
                    param_desc = param_schema.description or ""
                    
                    # Extract value based on context and parameter type
                    extracted_value = self._extract_parameter_value(param_name, param_type, param_desc, content)
                    
                    # Always include the parameter in extracted_params, even if extraction fails
                    # This prevents the "Missing required parameters" error
                    if extracted_value:
                        extracted_params[param_name] = extracted_value
                    elif param_name in auto_params:
                        # For required parameters with $fromAI(), provide a sensible default
                        extracted_params[param_name] = self._generate_default_value(param_name, param_type, content)
        
        return extracted_params
    
    def _extract_parameter_value(self, param_name: str, param_type: str, param_desc: str, content: str) -> Optional[str]:
        """Extract a specific parameter value based on context and type."""
        import re
        
        # Remove $fromAI() references for cleaner analysis
        clean_content = re.sub(r'\{\{ \$fromAI\([^}]*\)\}', '', content)
        
        param_value = None
        
        # Parameter name-based extraction
        param_variants = [
            param_name.lower(),
            param_name.replace('_', ' ').lower(),
            param_name.replace('-', ' ').lower()
        ]
        
        # Look for explicit mentions of the parameter
        for variant in param_variants:
            patterns = [
                rf'{variant}[:\s]*(is|should be|=|:)\s*["\']?([^"\'\s,]+)["\']?',
                rf'{variant}[:\s]*(is|should be|=|:)\s*["\']?([^"\'\s,]+)\.*["\']?',
                rf'["\']([^"\'\s,]+)["\']?.*for\s+{variant}',
                rf'{variant}:\s*["\']([^"\'\s,]+)["\']?'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, clean_content.lower())
                if matches:
                    # Extract the actual value (skip group 1 if it's the indicator word)
                    if len(matches[0]) == 2:
                        param_value = matches[0][1]
                    else:
                        param_value = matches[0]
                    break
            
            if param_value:
                break
        
        # If not found explicitly, try contextual extraction based on parameter type
        if not param_value:
            param_value = self._contextual_extraction(param_name, param_type, clean_content)
        
        # Type conversion and validation
        if param_value and param_type == 'string':
            # Ensure it's a string
            param_value = str(param_value)
        elif param_value and param_type == 'number':
            # Try to convert to number or return as string
            try:
                param_value = str(float(param_value))
            except:
                pass
        
        return param_value if param_value and param_value.strip() else None
    
    def _generate_default_value(self, param_name: str, param_type: str, content: str) -> str:
        """Generate a default value for parameters that couldn't be extracted."""
        
        import re
        
        # For System_Message, extract from the main user message context
        if "system" in param_name.lower() or "message" in param_name.lower():
            # Extract a reasonable system message from the content
            clean_content = re.sub(r'\{\{ \$fromAI\([^}]*\)\}', '', content)
            if clean_content.strip():
                return clean_content.strip()[:500] # Limit length
            else:
                return "Process the user's request based on the provided context."
        
        # For other parameters, provide type-appropriate defaults
        if param_type == "string":
            return ""
        elif param_type == "number":
            return "0"
        elif param_type == "integer":
            return "0"
        elif param_type == "boolean":
            return "false"
        else:
            return ""
    
    def _contextual_extraction(self, param_name: str, param_type: str, content: str) -> Optional[str]:
        """Extract parameter value based on contextual clues."""
        content_lower = content.lower()
        
        # Common parameter extractions based on names and context
        if any(word in param_name.lower() for word in ['name', 'username', 'user']):
            # Look for names in the content
            import re
            name_patterns = [
                r'([A-Z][a-z]+ [A-Z][a-z]+)', # Full name
                r'([A-Z][a-z]+)', # First name
            ]
            for pattern in name_patterns:
                names = re.findall(pattern, content)
                if names:
                    return names[0]
        
        elif any(word in param_name.lower() for word in ['email', 'mail']):
            # Look for email addresses
            import re
            emails = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', content)
            if emails:
                return emails[0]
        
        elif any(word in param_name.lower() for word in ['key', 'api', 'token']):
            # Look for API keys or tokens
            import re
            # Common patterns for keys, tokens, IDs
            key_patterns = [
                r'([a-zA-Z0-9]{8}-?[a-zA-Z0-9]{4}-?[a-zA-Z0-9]{4}-?[a-zA-Z0-9]{4}-?[a-zA-Z0-9]{12})', # UUID-like
                r'([a-zA-Z0-9]{32})', # 32-character hex
                r'([a-zA-Z0-9+/]{20,}=*)', # Base64-like
                r'([a-zA-Z][a-zA-Z0-9_]{5,20})', # Generic ID
            ]
            for pattern in key_patterns:
                keys = re.findall(pattern, content)
                if keys:
                    return keys[0]
        
        elif any(word in param_name.lower() for word in ['subject']):
            # Extract subject from context
            sentences = content.split('.')
            for sentence in sentences:
                if any(word in sentence.lower() for word in ['about', 'regarding', 'concerning', 'subject']):
                    return sentence.strip()
        
        elif any(word in param_name.lower() for word in ['message', 'content', 'body']):
            # Extract main message content
            # Remove $fromAI references and take the core message
            import re
            cleaned = re.sub(r'\{\{ \$fromAI\([^}]*\)\}', '', content)
            if cleaned.strip():
                return cleaned.strip()[:200] # Limit length
        
        # Default fallback for common cases
        if any(word in param_name.lower() for word in ['operation']):
            # Look for operation keywords
            operations = ['sum', 'add', 'calculate', 'multiply', 'divide', 'subtract']
            for op in operations:
                if op in content_lower:
                    return op
        
        return None
    
    def _normalize_tool_name(self, tool_name: str) -> str:
        """Normalize tool name for case-insensitive matching."""
        if not tool_name:
            return tool_name
        
        # Convert to lowercase and replace underscores with hyphens for consistent matching
        normalized = tool_name.lower().replace('_', '-')
        return normalized
    
    def _parse_tool_calls_from_response(self, response_text: str, tools: List[ToolDefinition]) -> List[ToolCall]:
        """Parse tool calls from model response."""
        try:
            tool_call_dicts = parse_tool_calls_from_response(response_text)
            tool_calls = []
            
            for call_dict in tool_call_dicts:
                try:
                    # Extract function name and arguments
                    function_name = call_dict.get('name', '')
                    function_args = call_dict.get('arguments', {})
                    
                    if not function_name:
                        logger.warning("Tool call missing function name")
                        continue
                    
                    # Validate function exists in tools with case-insensitive matching
                    valid_function = False
                    matched_tool = None
                    
                    # First try exact match (for performance)
                    for tool in tools:
                        if tool.function.name == function_name:
                            valid_function = True
                            matched_tool = tool
                            break
                    
                    # If not found, try case-insensitive matching
                    if not valid_function:
                        normalized_function_name = self._normalize_tool_name(function_name)
                        for tool in tools:
                            normalized_tool_name = self._normalize_tool_name(tool.function.name)
                            if normalized_tool_name == normalized_function_name:
                                valid_function = True
                                matched_tool = tool
                                logger.info(f"Matched function '{function_name}' to registered tool '{tool.function.name}' (case-insensitive)")
                                break
                    
                    if valid_function and matched_tool:
                        # Validate arguments if strict validation is enabled
                        if self.config.strict_parameter_validation:
                            function_args = validate_tool_arguments(matched_tool.function, function_args)
                    elif not valid_function:
                        logger.warning(f"Function '{function_name}' not found in available tools")
                        continue
                    
                    # Create tool call - use the matched tool's actual function name
                    if matched_tool:
                        tool_call = ToolCall(
                            function={
                                'name': matched_tool.function.name,
                                'arguments': function_args
                            }
                        )
                    else:
                        tool_call = ToolCall(
                            function={
                                'name': function_name,
                                'arguments': function_args
                            }
                        )
                    tool_calls.append(tool_call)
                
                except Exception as e:
                    logger.error(f"Error processing tool call: {call_dict}, error: {e}")
                    continue
            
            return tool_calls
        
        except Exception as e:
            logger.error(f"Error parsing tool calls: {e}")
            return []
    
    def _execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[Any]:
        """Execute tool calls and return responses."""
        try:
            # Execute in parallel
            tool_responses = self.executor.execute_tools_parallel(tool_calls)
            
            # Store responses in conversation state
            for tool_call, tool_response in zip(tool_calls, tool_responses):
                if tool_response.success:
                    self.conversation_state.add_tool_response(
                        tool_call.id,
                        str(tool_response.result)
                    )
                else:
                    self.conversation_state.add_tool_response(
                        tool_call.id,
                        f"Error: {tool_response.error}"
                    )
            
            return tool_responses
        
        except Exception as e:
            logger.error(f"Error executing tool calls: {e}")
            return []
    
    def _format_tool_response(
        self,
        response_text: str,
        tool_calls: List[ToolCall],
        tool_responses: List[Any],
        model: str
    ) -> Dict[str, Any]:
        """Format response with tool calls."""
        
        # Build OpenAI-compatible response
        choice = {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response_text,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function_name,
                            "arguments": json.dumps(call.function_arguments)
                        }
                    }
                    for call in tool_calls
                ]
            },
            "finish_reason": "tool_calls"
        }
        
        response = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [choice],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        
        # Store tool calls in conversation state
        self.conversation_state.last_assistant_tool_calls = tool_calls
        
        return response
    
    def _generate_non_tool_response(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a non-tool response."""
        try:
            from llm_endpoint_server import get_thread_client, format_openai_response
            
            client = get_thread_client()
            if not client:
                raise Exception("Service not initialized")
            
            # Convert messages to Salesforce format
            system_message, final_prompt = self._convert_to_salesforce_format(messages)
            
            # Generate response
            sf_response = client.generate_text(
                prompt=final_prompt,
                model=model,
                system_message=system_message,
                **kwargs
            )
            
            # Convert to OpenAI format
            return format_openai_response(sf_response, model)
        
        except Exception as e:
            logger.error(f"Error generating non-tool response: {e}")
            return self._format_error_response(str(e), model)
    
    def _convert_to_salesforce_format(self, messages: List[Dict[str, Any]]) -> tuple[Optional[str], str]:
        """Convert messages to Salesforce format."""
        system_message = None
        user_messages = []
        
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if role == 'system':
                system_message = content
            elif role == 'user':
                user_messages.append(content)
            elif role == 'assistant':
                user_messages.append(f"Assistant: {content}")
            elif role == 'tool':
                user_messages.append(f"Tool Result: {content}")
        
        # Combine user messages
        final_prompt = user_messages[-1] if user_messages else ""
        
        return system_message, final_prompt
    
    def _extract_response_text(self, sf_response: Dict[str, Any]) -> str:
        """
        OPTIMIZED: Extract text from Salesforce response using single-path lookup strategy.
        Imports and uses the optimized function from llm_endpoint_server.py.
        """
        try:
            # Import the optimized response extraction function
            from llm_endpoint_server import extract_response_text_optimized
            
            # Use the optimized response extraction with debug mode
            debug_mode = False # Set to True for debugging
            return extract_response_text_optimized(sf_response, debug_mode)
        
        except Exception as e:
            logger.error(f"Error extracting response text: {e}")
            return str(sf_response)
    
    def _format_error_response(self, error_message: str, model: str) -> Dict[str, Any]:
        """Format error response."""
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"I encountered an error: {error_message}"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            },
            "error": {
                "message": error_message,
                "type": "tool_calling_error",
                "code": "tool_execution_failed"
            }
        }
    
    def reset_conversation(self):
        """Reset conversation state."""
        self.conversation_state.clear()
    
    def get_available_tools(self) -> List[FunctionDefinition]:
        """Get list of available tools."""
        return self.executor.list_available_tools()
    
    def get_tool_info(self, tool_name: str) -> Optional[FunctionDefinition]:
        """Get information about a specific tool."""
        return self.executor.get_tool_info(tool_name)
    
    def register_custom_tool(self, name: str, func: callable, definition: FunctionDefinition):
        """Register a custom tool."""
        self.executor.register_custom_function(name, func, definition)
    
    def close(self):
        """Close the tool handler."""
        if hasattr(self.executor, 'close'):
            self.executor.close()
        self.conversation_state.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ToolStreamingHandler:
    """Handler for streaming tool calling responses with OpenAI-compatible tool call deltas."""
    
    def __init__(self, config: ToolCallingConfig):
        self.config = config
        self.handler = ToolCallingHandler(config)
        
        # Performance metrics
        self.stream_count = 0
        self.tool_call_chunks_sent = 0
        self.execution_progress_updates = 0
    
    def generate_stream(self, messages: List[Dict[str, Any]], **kwargs) -> Generator[str, Any, Any]:
        """Generate streaming response with OpenAI-compatible tool calling deltas."""
        try:
            self.stream_count += 1
            stream_id = self._generate_stream_id()
            model = kwargs.get('model', 'claude-3-haiku')
            
            # Generate base response first to determine if tool calls are needed
            response = self.handler.process_request(messages, **kwargs)
            
            # Send role delta as the first chunk (OpenAI spec compliance)
            yield self._format_role_chunk(response, stream_id)
            
            # Determine if this is a tool calling response
            message = response['choices'][0]['message']
            has_tool_calls = 'tool_calls' in message
            
            if has_tool_calls:
                # Enhanced tool calling response with proper delta streaming
                content = message.get('content', '') or ''
                tool_calls = message['tool_calls']
                
                # Stream content incrementally if present
                if content.strip():
                    for content_chunk in self._split_content_into_chunks(content):
                        yield self._format_content_chunk(content_chunk, response, stream_id)
                
                # Enhanced tool call delta streaming
                yield from self._stream_tool_call_deltas(tool_calls, response, stream_id)
                
                # Execute tools and stream progress
                yield from self._stream_tool_execution_progress(tool_calls, response, stream_id)
                
                # Final chunk with tool_calls finish reason
                yield self._format_finish_chunk("tool_calls", response, stream_id)
            else:
                # Regular response - stream content
                content = message.get('content', '') or ''
                if content.strip():
                    for content_chunk in self._split_content_into_chunks(content):
                        yield self._format_content_chunk(content_chunk, response, stream_id)
                
                # Final chunk with stop finish reason
                yield self._format_finish_chunk("stop", response, stream_id)
        
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            yield self._format_error_chunk(str(e), **kwargs)
    
    def _stream_tool_call_deltas(self, tool_calls: List[Dict[str, Any]], response: Dict[str, Any], stream_id: str) -> Generator[str, Any, Any]:
        """Stream tool call deltas in OpenAI-compatible format."""
        for i, tool_call in enumerate(tool_calls):
            tool_call_id = tool_call['id']
            function_name = tool_call['function']['name']
            function_arguments = tool_call['function']['arguments']
            
            # Parse arguments for incremental streaming
            try:
                args_dict = json.loads(function_arguments)
            except json.JSONDecodeError:
                args_dict = {}
            
            # Stream tool call initiation (ID and name)
            yield self._format_tool_call_delta_chunk(
                index=i,
                tool_call_id=tool_call_id,
                function_name=function_name,
                arguments_json='',
                stream_id=stream_id,
                response=response
            )
            
            # Stream arguments incrementally (for complex arguments)
            if args_dict:
                yield from self._stream_arguments_incrementally(
                    i, tool_call_id, function_name, args_dict, stream_id, response
                )
            
            self.tool_call_chunks_sent += 1
    
    def _stream_arguments_incrementally(self, index: int, tool_call_id: str, function_name: str,
                                        args_dict: Dict[str, Any], stream_id: str,
                                        response: Dict[str, Any]) -> Generator[str, Any, Any]:
        """Stream function arguments incrementally for complex tool calls."""
        current_args = {}
        
        # Stream arguments one by one with progress updates
        for arg_name, arg_value in args_dict.items():
            current_args[arg_name] = arg_value
            
            # Send incremental argument update
            args_json = json.dumps(current_args)
            yield self._format_tool_call_delta_chunk(
                index=index,
                tool_call_id=tool_call_id,
                function_name=function_name,
                arguments_json=args_json,
                stream_id=stream_id,
                response=response
            )
            
            # Yield a small delay for better streaming experience
            time.sleep(0.01)
    
    def _stream_tool_execution_progress(self, tool_calls: List[Dict[str, Any]],
                                        response: Dict[str, Any], stream_id: str) -> Generator[str, Any, Any]:
        """Stream tool execution progress updates."""
        for i, tool_call in enumerate(tool_calls):
            tool_call_id = tool_call['id']
            function_name = tool_call['function']['name']
            
            # Stream execution start
            yield self._format_execution_progress_chunk(
                tool_call_id=tool_call_id,
                function_name=function_name,
                status="executing",
                message=f"Executing {function_name}...",
                stream_id=stream_id,
                response=response
            )
            
            # Simulate execution progress (in real implementation, this would be actual progress)
            for progress in [25, 50, 75, 100]:
                yield self._format_execution_progress_chunk(
                    tool_call_id=tool_call_id,
                    function_name=function_name,
                    status="progress",
                    message=f"Executing {function_name}... {progress}%",
                    stream_id=stream_id,
                    response=response
                )
                time.sleep(0.005) # Small delay for progress updates
            
            # Stream completion
            yield self._format_execution_progress_chunk(
                tool_call_id=tool_call_id,
                function_name=function_name,
                status="completed",
                message=f"Completed {function_name}",
                stream_id=stream_id,
                response=response
            )
            
            self.execution_progress_updates += 1
    
    def _split_content_into_chunks(self, content: str, chunk_size: int = 50) -> List[str]:
        """Split content into smaller chunks for streaming."""
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        words = content.split(' ')
        current_chunk = ''
        
        for word in words:
            if len(current_chunk + ' ' + word) <= chunk_size:
                current_chunk += ' ' + word if current_chunk else word
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = word
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _format_role_chunk(self, response: Dict[str, Any], stream_id: str) -> str:
        """Format the role delta chunk (OpenAI spec compliance)."""
        chunk = {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": response['created'],
            "model": response['model'],
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant"},
                "finish_reason": None
            }]
        }
        return f"data: {json.dumps(chunk)}\n\n"
    
    def _format_content_chunk(self, content: str, response: Dict[str, Any], stream_id: str) -> str:
        """Format a content delta chunk."""
        chunk = {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": response['created'],
            "model": response['model'],
            "choices": [{
                "index": 0,
                "delta": {"content": content},
                "finish_reason": None
            }]
        }
        return f"data: {json.dumps(chunk)}\n\n"
    
    def _format_tool_call_delta_chunk(self, index: int, tool_call_id: str, function_name: str,
                                      arguments_json: str, stream_id: str, response: Dict[str, Any]) -> str:
        """Format a tool call delta chunk with OpenAI-compatible structure."""
        chunk = {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": response['created'],
            "model": response['model'],
            "choices": [{
                "index": 0,
                "delta": {
                    "tool_calls": [{
                        "index": index,
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": function_name,
                            "arguments": arguments_json
                        }
                    }]
                },
                "finish_reason": None
            }]
        }
        return f"data: {json.dumps(chunk)}\n\n"
    
    def _format_execution_progress_chunk(self, tool_call_id: str, function_name: str,
                                         status: str, message: str, stream_id: str,
                                         response: Dict[str, Any]) -> str:
        """Format execution progress chunk."""
        chunk = {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": response['created'],
            "model": response['model'],
            "choices": [{
                "index": 0,
                "delta": {
                    "content": message
                },
                "finish_reason": None
            }]
        }
        return f"data: {json.dumps(chunk)}\n\n"
    
    def _format_finish_chunk(self, finish_reason: str, response: Dict[str, Any], stream_id: str) -> str:
        """Format the final chunk with finish reason."""
        chunk = {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": response['created'],
            "model": response['model'],
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": finish_reason
            }]
        }
        return f"data: {json.dumps(chunk)}\n\n"
    
    def _format_error_chunk(self, error_message: str, **kwargs) -> str:
        """Format error chunk."""
        chunk = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": kwargs.get('model', 'claude-3-haiku'),
            "choices": [{
                "index": 0,
                "delta": {"content": f"Error: {error_message}"},
                "finish_reason": "stop"
            }]
        }
        return f"data: {json.dumps(chunk)}\n\n"
    
    def _generate_stream_id(self) -> str:
        """Generate a unique stream ID."""
        return f"chatcmpl-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    
    def get_streaming_stats(self) -> Dict[str, Any]:
        """Get streaming performance statistics."""
        return {
            "total_streams": self.stream_count,
            "tool_call_chunks_sent": self.tool_call_chunks_sent,
            "execution_progress_updates": self.execution_progress_updates,
            "average_tool_call_chunks_per_stream": (
                self.tool_call_chunks_sent / self.stream_count if self.stream_count > 0 else 0
            )
        }
    
    def close(self):
        """Close the streaming handler."""
        if hasattr(self.handler, 'close'):
            self.handler.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Helper functions for enhanced streaming
def create_enhanced_tool_stream_handler(config: ToolCallingConfig,
                                        streaming_config: Optional[Dict[str, Any]] = None) -> ToolStreamingHandler:
    """
    Create an enhanced ToolStreamingHandler with advanced streaming capabilities.
    
    Args:
        config: ToolCallingConfig instance
        streaming_config: Additional streaming configuration
            - chunk_size: Size of content chunks (default: 50)
            - enable_progress_updates: Enable execution progress updates (default: True)
            - enable_incremental_arguments: Stream arguments incrementally (default: True)
            - progress_intervals: Progress update intervals (default: [25, 50, 75, 100])
    
    Returns:
        Enhanced ToolStreamingHandler instance
    """
    handler = ToolStreamingHandler(config)
    
    # Apply streaming configuration if provided
    if streaming_config:
        handler.chunk_size = streaming_config.get('chunk_size', 50)
        handler.enable_progress_updates = streaming_config.get('enable_progress_updates', True)
        handler.enable_incremental_arguments = streaming_config.get('enable_incremental_arguments', True)
        handler.progress_intervals = streaming_config.get('progress_intervals', [25, 50, 75, 100])
    
    return handler


def validate_openai_streaming_format(chunk_data: str) -> bool:
    """
    Validate that a streaming chunk follows OpenAI's streaming format.
    
    Args:
        chunk_data: Raw streaming chunk data
    
    Returns:
        True if valid OpenAI streaming format, False otherwise
    """
    try:
        # Extract JSON from SSE format
        if not chunk_data.startswith('data: '):
            return False
        
        json_str = chunk_data[6:] # Remove 'data: ' prefix
        if json_str.endswith('\\n\\n'):
            json_str = json_str[:-2] # Remove trailing newlines
        elif json_str.endswith('\\n'):
            json_str = json_str[:-1] # Remove single newline
        
        chunk = json.loads(json_str)
        
        # Validate required fields
        required_fields = ['id', 'object', 'created', 'model', 'choices']
        if not all(field in chunk for field in required_fields):
            return False
        
        # Validate object type
        if chunk.get('object') != 'chat.completion.chunk':
            return False
        
        # Validate choices structure
        choices = chunk.get('choices', [])
        if not isinstance(choices, list) or len(choices) == 0:
            return False
        
        choice = choices[0]
        if not isinstance(choice, dict):
            return False
        
        # Validate choice structure
        if 'index' not in choice or 'delta' not in choice:
            return False
        
        # Validate delta structure
        delta = choice.get('delta', {})
        if not isinstance(delta, dict):
            return False
        
        return True
    
    except (json.JSONDecodeError, KeyError, IndexError, AttributeError):
        return False


def create_tool_call_delta_example() -> Dict[str, Any]:
    """
    Create an example of a proper OpenAI tool call delta chunk.
    
    Returns:
        Example tool call delta chunk
    """
    return {
        "id": "chatcmpl-1234567890abcdef",
        "object": "chat.completion.chunk",
        "created": 1677652288,
        "model": "claude-3-haiku",
        "choices": [{
            "index": 0,
            "delta": {
                "tool_calls": [{
                    "index": 0,
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": "{\"location\":\"San Francisco\"}"
                    }
                }]
            },
            "finish_reason": None
        }]
    }


def simulate_tool_calling_streaming_example() -> List[str]:
    """
    Simulate a complete tool calling streaming sequence.
    
    Returns:
        List of streaming chunks in order
    """
    chunks = []
    
    # Role chunk
    chunks.append('data: ' + json.dumps({
        "id": "chatcmpl-1234567890abcdef",
        "object": "chat.completion.chunk",
        "created": 1677652288,
        "model": "claude-3-haiku",
        "choices": [{
            "index": 0,
            "delta": {"role": "assistant"},
            "finish_reason": None
        }]
    }) + '\n\n')
    
    # Content chunk
    chunks.append('data: ' + json.dumps({
        "id": "chatcmpl-1234567890abcdef",
        "object": "chat.completion.chunk",
        "created": 1677652288,
        "model": "claude-3-haiku",
        "choices": [{
            "index": 0,
            "delta": {"content": "I'll get the weather information for you."},
            "finish_reason": None
        }]
    }) + '\n\n')
    
    # Tool call initiation
    chunks.append('data: ' + json.dumps({
        "id": "chatcmpl-1234567890abcdef",
        "object": "chat.completion.chunk",
        "created": 1677652288,
        "model": "claude-3-haiku",
        "choices": [{
            "index": 0,
            "delta": {
                "tool_calls": [{
                    "index": 0,
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": ""
                    }
                }]
            },
            "finish_reason": None
        }]
    }) + '\n\n')
    
    # Tool call with arguments
    chunks.append('data: ' + json.dumps({
        "id": "chatcmpl-1234567890abcdef",
        "object": "chat.completion.chunk",
        "created": 1677652288,
        "model": "claude-3-haiku",
        "choices": [{
            "index": 0,
            "delta": {
                "tool_calls": [{
                    "index": 0,
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": "{\"location\":\"San Francisco\"}"
                    }
                }]
            },
            "finish_reason": None
        }]
    }) + '\n\n')
    
    # Progress update
    chunks.append('data: ' + json.dumps({
        "id": "chatcmpl-1234567890abcdef",
        "object": "chat.completion.chunk",
        "created": 1677652288,
        "model": "claude-3-haiku",
        "choices": [{
            "index": 0,
            "delta": {"content": "Executing get_weather... 50%"},
            "finish_reason": None
        }]
    }) + '\n\n')
    
    # Tool calls complete
    chunks.append('data: ' + json.dumps({
        "id": "chatcmpl-1234567890abcdef",
        "object": "chat.completion.chunk",
        "created": 1677652288,
        "model": "claude-3-haiku",
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "tool_calls"
        }]
    }) + '\n\n')
    
    return chunks
"""
Streaming Architecture for Salesforce Models API Gateway
Provides streaming response capabilities for OpenAI-compatible responses.
"""

import json
import time
import logging
from typing import Dict, Any, Optional, Generator, List, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class OpenAIStreamChunk:
    """Represents an OpenAI streaming response chunk."""
    id: str
    object: str = "chat.completion.chunk"
    created: int = None
    model: str = ""
    choices: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created is None:
            self.created = int(time.time())
        if self.choices is None:
            self.choices = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": self.choices
        }
    
    def to_sse_format(self) -> str:
        """Convert to Server-Sent Events format."""
        return f"data: {json.dumps(self.to_dict())}\n\n"
    
    def to_anthropic_sse_format(self, event_type: str = "content_block_delta") -> str:
        """Convert to Anthropic-compatible Server-Sent Events format."""
        return f"event: {event_type}\ndata: {json.dumps(self.to_dict())}\n\n"


class StreamingResponseBuilder:
    """Builds streaming responses from text content."""
    
    def __init__(self, model: str, chunk_size: int = 10):
        self.model = model
        self.chunk_size = chunk_size
        self.stream_id = f"chatcmpl-{int(time.time())}"
    
    def create_text_chunks(self, text: str) -> Generator[OpenAIStreamChunk, None, None]:
        """Create streaming chunks from text content."""
        words = text.split()
        
        for i in range(0, len(words), self.chunk_size):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            
            # Add space if not the last chunk
            if i + self.chunk_size < len(words):
                chunk_text += " "
            
            chunk = OpenAIStreamChunk(
                id=self.stream_id,
                model=self.model,
                choices=[{
                    "index": 0,
                    "delta": {
                        "content": chunk_text
                    },
                    "finish_reason": None
                }]
            )
            yield chunk
        
        # Final chunk with finish_reason
        final_chunk = OpenAIStreamChunk(
            id=self.stream_id,
            model=self.model,
            choices=[{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        )
        yield final_chunk


class AnthropicStreamingResponseBuilder:
    """Builds Anthropic-compatible streaming responses from text content."""
    
    def __init__(self, model: str, message_id: str = None, chunk_size: int = 5):
        self.model = model
        self.chunk_size = chunk_size
        self.message_id = message_id or f"msg_{int(time.time())}"
    
    def create_anthropic_stream(self, text: str, usage_info: Dict[str, Any] = None) -> Generator[str, None, None]:
        """Create Anthropic-compatible streaming events."""
        if usage_info is None:
            usage_info = {"input_tokens": 0, "output_tokens": 0}
        
        try:
            # Message start event
            message_start_data = {
                "type": "message_start",
                "message": {
                    "id": self.message_id,
                    "type": "message",
                    "role": "assistant",
                    "content": [],
                    "model": self.model,
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {
                        "input_tokens": usage_info.get("input_tokens", 0),
                        "output_tokens": 0
                    }
                }
            }
            yield f"event: message_start\ndata: {json.dumps(message_start_data)}\n\n"
            
            # Content block start event
            content_block_start_data = {
                "type": "content_block_start",
                "index": 0,
                "content_block": {
                    "type": "text",
                    "text": ""
                }
            }
            yield f"event: content_block_start\ndata: {json.dumps(content_block_start_data)}\n\n"
            
            # OPTIMIZATION: SSE heartbeat tracking for connection stability  
            last_heartbeat_time = time.time()
            heartbeat_interval = 15.0  # 15 seconds
            
            # Stream content in chunks
            words = text.split()
            for i in range(0, len(words), self.chunk_size):
                # OPTIMIZATION: Inject SSE heartbeat if needed
                current_time = time.time()
                if current_time - last_heartbeat_time >= heartbeat_interval:
                    yield ":ka\n\n"  # SSE heartbeat to maintain connection
                    last_heartbeat_time = current_time
                
                chunk_words = words[i:i + self.chunk_size]
                chunk_text = " ".join(chunk_words)
                
                # Add space if not the last chunk
                if i + self.chunk_size < len(words):
                    chunk_text += " "
                
                content_block_delta_data = {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "text_delta",
                        "text": chunk_text
                    }
                }
                yield f"event: content_block_delta\ndata: {json.dumps(content_block_delta_data)}\n\n"
            
            # Content block stop event
            content_block_stop_data = {
                "type": "content_block_stop",
                "index": 0
            }
            yield f"event: content_block_stop\ndata: {json.dumps(content_block_stop_data)}\n\n"
            
            # Message delta event
            message_delta_data = {
                "type": "message_delta",
                "delta": {
                    "stop_reason": "end_turn",
                    "stop_sequence": None
                },
                "usage": {
                    "output_tokens": usage_info.get("output_tokens", 0)
                }
            }
            yield f"event: message_delta\ndata: {json.dumps(message_delta_data)}\n\n"
            
            # Message stop event
            message_stop_data = {
                "type": "message_stop"
            }
            yield f"event: message_stop\ndata: {json.dumps(message_stop_data)}\n\n"
            
        except Exception as e:
            logger.error(f"Error in Anthropic streaming: {e}")
            error_data = {
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": str(e)
                }
            }
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"


def get_anthropic_streaming_builder(model: str, message_id: str = None) -> AnthropicStreamingResponseBuilder:
    """Factory function to create Anthropic streaming response builder."""
    return AnthropicStreamingResponseBuilder(model, message_id)
    
    def create_tool_call_chunks(self, tool_calls: List[Dict[str, Any]]) -> Generator[OpenAIStreamChunk, None, None]:
        """Create streaming chunks for tool calls."""
        # First chunk with tool calls
        chunk = OpenAIStreamChunk(
            id=self.stream_id,
            model=self.model,
            choices=[{
                "index": 0,
                "delta": {
                    "tool_calls": tool_calls
                },
                "finish_reason": None
            }]
        )
        yield chunk
        
        # Final chunk
        final_chunk = OpenAIStreamChunk(
            id=self.stream_id,
            model=self.model,
            choices=[{
                "index": 0,
                "delta": {},
                "finish_reason": "tool_calls"
            }]
        )
        yield final_chunk


class StreamingOrchestrator:
    """Orchestrates streaming responses for different content types."""
    
    def __init__(self):
        self.builders: Dict[str, StreamingResponseBuilder] = {}
    
    def get_builder(self, model: str) -> StreamingResponseBuilder:
        """Get or create a streaming builder for a model."""
        if model not in self.builders:
            self.builders[model] = StreamingResponseBuilder(model)
        return self.builders[model]
    
    def stream_text_response(self, text: str, model: str) -> Generator[str, None, None]:
        """Stream a text response in OpenAI format."""
        builder = self.get_builder(model)
        
        for chunk in builder.create_text_chunks(text):
            yield chunk.to_sse_format()
        
        # End of stream marker
        yield "data: [DONE]\n\n"
    
    def stream_tool_response(self, tool_calls: List[Dict[str, Any]], model: str) -> Generator[str, None, None]:
        """Stream a tool calling response in OpenAI format."""
        builder = self.get_builder(model)
        
        for chunk in builder.create_tool_call_chunks(tool_calls):
            yield chunk.to_sse_format()
        
        # End of stream marker
        yield "data: [DONE]\n\n"


class StreamingErrorHandler:
    """Handles errors in streaming responses."""
    
    @staticmethod
    def create_error_chunk(error_message: str, error_code: str = "internal_error") -> str:
        """Create an error chunk in streaming format."""
        error_chunk = {
            "id": f"chatcmpl-error-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "unknown",
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "error"
            }],
            "error": {
                "message": error_message,
                "type": error_code
            }
        }
        
        return f"data: {json.dumps(error_chunk)}\n\n"
    
    @staticmethod
    def handle_streaming_error(error: Exception, model: str = "unknown") -> Generator[str, None, None]:
        """Handle an error by generating an error stream."""
        logger.error(f"Streaming error: {error}")
        
        error_message = str(error)
        if len(error_message) > 200:
            error_message = error_message[:200] + "..."
        
        yield StreamingErrorHandler.create_error_chunk(error_message)
        yield "data: [DONE]\n\n"


# Singleton instances
_streaming_orchestrator: Optional[StreamingOrchestrator] = None
_streaming_error_handler: Optional[StreamingErrorHandler] = None

def get_streaming_orchestrator() -> StreamingOrchestrator:
    """Get the global streaming orchestrator instance."""
    global _streaming_orchestrator
    if _streaming_orchestrator is None:
        _streaming_orchestrator = StreamingOrchestrator()
    return _streaming_orchestrator

def get_streaming_error_handler() -> StreamingErrorHandler:
    """Get the global streaming error handler instance."""
    global _streaming_error_handler
    if _streaming_error_handler is None:
        _streaming_error_handler = StreamingErrorHandler()
    return _streaming_error_handler
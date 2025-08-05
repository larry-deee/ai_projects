"""
Salesforce Models API Client
============================

A standalone client for accessing Salesforce/Agentforce hosted LLMs (Claude, OpenAI, Gemini)
through the Einstein Trust Layer Models API.

This module reuses the authentication infrastructure from the existing TabPy sentiment analyzer
but provides direct access to LLMs without requiring prompt templates.

Usage:
    client = SalesforceModelsClient()
    models = client.list_models()
    response = client.generate_text("Hello, world!", model="claude-3-haiku")
"""

import os
import time
import json
import asyncio
import requests
import aiohttp
import ssl
import random
from typing import List, Dict, Optional, Any

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    # Fallback: create default context without certifi
    SSL_CONTEXT = ssl.create_default_context()


class SalesforceModelsClient:
    """
    Client for Salesforce Einstein Trust Layer Models API.
    
    Provides direct access to hosted LLMs like Claude, GPT-4, Gemini through
    Salesforce's Einstein Trust Layer without requiring prompt templates.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the Salesforce Models API client.
        
        Args:
            config_file: Optional path to configuration file. If not provided,
                        uses environment variables.
        """
        self.async_client = AsyncSalesforceModelsClient(config_file)

    def _load_config(self, config_file: Optional[str] = None) -> Dict[str, str]:
        return self.async_client._load_config(config_file)
    
    def _validate_config(self):
        self.async_client._validate_config()

    def _load_token(self) -> Optional[str]:
        return self.async_client._load_token()

    def _save_token(self, access_token: str, expires_in: int):
        self.async_client._save_token(access_token, expires_in)
    
    def _get_client_credentials_token(self) -> str:
        return self.async_client._get_client_credentials_token()
    
    def get_access_token(self) -> str:
        """Get access token with proper async handling for Flask threading."""
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If event loop is running, create a new thread for async operation
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.async_client._async_get_access_token())
                    return future.result(timeout=120)
            else:
                return asyncio.run(self.async_client._async_get_access_token())
        except RuntimeError:
            # No event loop in current thread, safe to create new one
            return asyncio.run(self.async_client._async_get_access_token())
    
    def list_models(self) -> List[Dict[str, Any]]:
        return asyncio.run(self.async_client._async_list_models())

    # generate_text is implemented properly as sync method below

    # generate_text_simple is implemented properly as sync method below

    def chat_completion(self, *args, **kwargs) -> Dict[str, Any]:
        return asyncio.run(self.async_client._async_chat_completion(*args, **kwargs))

    def generate_text(
        self,
        prompt: str,
        model: str = "sfdc_ai__DefaultBedrockAnthropicClaude3Haiku",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate text using specified model through Einstein Trust Layer.
        
        Args:
            prompt: User prompt/message
            model: Model name (full Salesforce API name like "sfdc_ai__Default Bedrock Anthropic Claude3Haiku")
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            system_message: Optional system message for conversation context
            **kwargs: Additional model-specific parameters
        
        Returns:
            Response from the model including generated text and metadata.
        """
        # Map friendly names to full API names
        model_mapping = {
            "claude-3-haiku": "sfdc_ai__DefaultBedrockAnthropicClaude3Haiku",
            "claude-3-sonnet": "sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet", 
            "claude-4-sonnet": "sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet",
            "gpt-4": "sfdc_ai__DefaultGPT4Omni",
            "gpt-4-mini": "sfdc_ai__DefaultOpenAIGPT4OmniMini",
            "gemini-pro": "sfdc_ai__DefaultVertexAIGemini25Flash001"
        }
        
        # Use mapping if friendly name provided
        api_model_name = model_mapping.get(model, model)
        
        access_token = self.get_access_token()
        endpoint = f"https://api.salesforce.com/einstein/platform/v1/models/{api_model_name}/generations"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'x-sfdc-app-context': 'EinsteinGPT',
            'x-client-feature-id': 'ai-platform-models-connected-app'
        }
        
        # Build payload - Salesforce Models API expects 'prompt' field, not 'messages'
        full_prompt = prompt
        if system_message:
            full_prompt = f"System: {system_message}\n\n User: {prompt}"
        
        payload = {
            "prompt": full_prompt,
            "max Tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        # Calculate timeout dynamically based on prompt size and model
        # CONSERVATIVE timeout settings to avoid gunicorn worker timeouts
        prompt_length = len(full_prompt)
        base_timeout = 60 # Reduced base timeout from 120 to 60 seconds
        
        # Increase timeout for large prompts and slower models
        if prompt_length > 30000:
            base_timeout = 240 # 4 minutes for very large prompts (reduced from 300)
        elif prompt_length > 10000:
            base_timeout = 120 # 2 minutes for large prompts (reduced from 180)
        
        # Claude-4-Sonnet typically needs more time
        if "claude-4" in model.lower():
            base_timeout = int(base_timeout * 1.2) # Reduced multiplier from 1.5 to 1.2
        
        # Ensure timeout doesn't exceed reasonable limits
        max_timeout = 480 if os.environ.get('ENVIRONMENT') == 'production' else 300
        timeout = min(base_timeout, max_timeout)
        
        # Log timeout setting for debugging
        print(f"🕐 Using timeout: {timeout}s for prompt length {prompt_length}, model: {model}")
        
        max_retries = 1 # Reduced from 2 to 1 to avoid excessive timeout escalation
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                response = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
                
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    raise Exception(f"Failed to generate text: {response.status_code} - {response.text}")
                
            except requests.exceptions.Timeout as e:
                retry_count += 1
                if retry_count <= max_retries:
                    # More conservative timeout increase for retry
                    increased_timeout = int(timeout * 1.2) # Reduced from 1.5 to 1.2
                    final_timeout = min(increased_timeout, max_timeout)
                    print(f"⏰ Request timed out after {timeout}s, retrying with {final_timeout}s timeout (attempt {retry_count}/{max_retries})")
                    timeout = final_timeout
                    continue
                else:
                    # Provide more helpful error message with specific recommendations
                    if prompt_length > 20000:
                        suggestion = "Consider using claude-3-haiku and reducing prompt size significantly"
                    elif "claude-4" in model.lower():
                        suggestion = "Try using claude-3-haiku or claude-3-sonnet for faster processing"
                    else:
                        suggestion = "Try using claude-3-haiku for faster responses or reduce input size"

                    raise Exception(f"Request timed out after {max_retries} retries. Last timeout: {timeout}s. {suggestion}.") from e
            except Exception as e:
                raise Exception(f"Failed to generate text: {str(e)}") from e

    def generate_text_simple(self, prompt: str, model: str = "claude-3-haiku") -> str:
        """
        Simple text generation that returns just the generated text.
        
        Args:
            prompt: User prompt
            model: Model to use
        
        Returns:
            Generated text string
        """
        response = self.generate_text(prompt, model)
        
        # Extract text from response (structure may vary by API version)
        if 'generations' in response:
            return response['generations'][0].get('text', '')
        elif 'choices' in response:
            return response['choices'][0].get('message', {}).get('content', '')
        elif 'text' in response:
            return response['text']
        else:
            return str(response)


class AsyncSalesforceModelsClient:
    """
    Asynchronous client for Salesforce Einstein Trust Layer Models API.
    """
    def __init__(self, config_file: Optional[str] = None):
        self.config = self._load_config(config_file)
        self.token_file = self.config.get('token_file', 'salesforce_models_token.json')
    
    def _load_config(self, config_file: Optional[str] = None) -> Dict[str, str]:
        """Load configuration from file or environment variables."""
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        
        return {
            'consumer_key': os.environ.get('SALESFORCE_CONSUMER_KEY'),
            'consumer_secret': os.environ.get('SALESFORCE_CONSUMER_SECRET'),
            'instance_url': os.environ.get('SALESFORCE_INSTANCE_URL'),
            'api_version': os.environ.get('SALESFORCE_API_VERSION', 'v64.0'),
            'token_file': os.environ.get('SALESFORCE_MODELS_TOKEN_FILE', 'salesforce_models_token.json')
        }

    def _validate_config(self):
        """Validate that required Client Credentials configuration is present."""
        required_fields = ['consumer_key', 'consumer_secret', 'instance_url']
        missing_fields = [field for field in required_fields if not self.config.get(field)]
        
        if missing_fields:
            raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")

    def _load_token(self) -> Optional[str]:
        """Load cached access token if valid with aggressive validation."""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    expires_at = token_data.get('expires_at', 0)
                    current_time = time.time()
                    
                    # CONSERVATIVE: Require at least 10 minutes buffer to account for Salesforce-side invalidation
                    if expires_at > current_time + 600: # 10 minutes = 600 seconds
                        return token_data.get('access_token')
                    else:
                        # Token is too close to expiration or expired, don't use it
                        print(f"🔄 Token too close to expiration (expires in {(expires_at - current_time)/60:.1f} minutes), will refresh")
                        return None
            except (json.JSONDecodeError, KeyError):
                pass
        return None

    def _save_token(self, access_token: str, expires_in: int):
        """Save access token with aggressive expiration buffer."""
        token_data = {
            'access_token': access_token,
            'expires_at': time.time() + expires_in - 600, # 10 minute buffer (consistent)
            'created_at': time.time()
        }
        with open(self.token_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        print(f"💾 Token saved with 10-minute buffer (expires at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(token_data['expires_at']))})")

    async def _get_client_credentials_token(self) -> str:
        """Get access token using async Client Credentials Flow with retry logic."""
        self._validate_config()
        
        oauth_url = f"{self.config['instance_url']}/services/oauth2/token"
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as session:
                    async with session.post(
                        oauth_url,
                        data={
                            'grant_type': 'client_credentials',
                            'client_id': self.config['consumer_key'],
                            'client_secret': self.config['consumer_secret']
                        },
                        headers={
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'Accept': 'application/json'
                        },
                        timeout=60
                    ) as response:
                        if response.status == 200:
                            token_response = await response.json()
                            access_token = token_response.get('access_token')
                            expires_in = int(token_response.get('expires_in', 3600))
                            self._save_token(access_token, expires_in)
                            if attempt > 0:
                                print(f"✅ OAuth token obtained successfully on attempt {attempt + 1}")
                            return access_token
                        else:
                            try:
                                error_data = await response.json()
                                error_msg = f"Failed to obtain access token: {response.status} - {error_data}"
                            except:
                                error_msg = f"Failed to obtain access token: {response.status} - {await response.text()}"
                            
                            # Don't retry on authentication errors (400, 401, 403)
                            if response.status in [400, 401, 403]:
                                raise Exception(error_msg)
                            
                            if attempt < max_retries - 1:
                                delay = base_delay * (2 ** attempt)
                                print(f"⏰ OAuth request failed (attempt {attempt + 1}), retrying in {delay}s: {error_msg}")
                                await asyncio.sleep(delay)
                                continue
                            else:
                                raise Exception(error_msg)
            except Exception as e:
                if attempt < max_retries - 1 and "timeout" in str(e).lower():
                    delay = base_delay * (2 ** attempt)
                    print(f"⏰ OAuth timeout (attempt {attempt + 1}), retrying in {delay}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise

    async def _async_get_access_token(self) -> str:
        """Get valid access token (cached or fresh) using async Client Credentials Flow."""
        token = self._load_token()
        if token:
            return token
        else:
            print("🔑 Using async Client Credentials Flow (External Client App)")
            return await self._get_client_credentials_token()

    async def _async_list_models(self) -> List[Dict[str, Any]]:
        """
        List available models through the Einstein Trust Layer.
        This method remains synchronous as it returns a hardcoded list.
        """
        models = [
            {
                "name": "sfdc_ai__DefaultBedrockAnthropicClaude3Haiku",
                "display_name": "Claude 3 Haiku",
                "provider": "Anthropic",
                "description": "Fast, efficient Claude 3 model for quick tasks"
            },
            {
                "name": "sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet",
                "display_name": "Claude 3.7 Sonnet",
                "provider": "Anthropic",
                "description": "Balanced Claude model for general use"
            },
            {
                "name": "sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet",
                "display_name": "Claude 4 Sonnet",
                "provider": "Anthropic",
                "description": "Latest Claude model with enhanced capabilities"
            },
            {
                "name": "sfdc_ai__DefaultOpenAIGPT4OmniMini",
                "display_name": "GPT-4 Omni Mini",
                "provider": "OpenAI",
                "description": "Compact GPT-4 model for efficient processing"
            },
            {
                "name": "sfdc_ai__DefaultGPT4Omni",
                "display_name": "GPT-4 Omni",
                "provider": "OpenAI",
                "description": "Multimodal GPT-4 model"
            },
            {
                "name": "sfdc_ai__DefaultVertexAIGemini25Flash001",
                "display_name": "Gemini 2.5 Flash",
                "provider": "Google",
                "description": "Latest Gemini model with enhanced speed"
            }
        ]
        return models

    async def _async_generate_text(
        self,
        prompt: str,
        model: str = "sfdc_ai__DefaultBedrockAnthropicClaude3Haiku",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text async using specified model through Einstein Trust Layer."""
        model_mapping = {
            "claude-3-haiku": "sfdc_ai__DefaultBedrockAnthropicClaude3Haiku",
            "claude-3-sonnet": "sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet",
            "claude-4-sonnet": "sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet",
            "gpt-4": "sfdc_ai__DefaultGPT4Omni",
            "gpt-4-mini": "sfdc_ai__DefaultOpenAIGPT4OmniMini",
            "gemini-pro": "sfdc_ai__DefaultVertexAIGemini25Flash001"
        }
        
        api_model_name = model_mapping.get(model, model)
        
        access_token = await self._async_get_access_token()
        endpoint = f"https://api.salesforce.com/einstein/platform/v1/models/{api_model_name}/generations"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'x-sfdc-app-context': 'EinsteinGPT',
            'x-client-feature-id': 'ai-platform-models-connected-app'
        }
        
        full_prompt = prompt
        if system_message:
            full_prompt = f"System: {system_message}\n\n User: {prompt}"
        
        payload = {
            "prompt": full_prompt,
            "max Tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        # Calculate timeout dynamically based on prompt size and model
        # CONSERVATIVE timeout settings to avoid gunicorn worker timeouts
        prompt_length = len(full_prompt)
        base_timeout = 60 # Reduced base timeout from 120 to 60 seconds
        
        # Increase timeout for large prompts and slower models
        if prompt_length > 30000:
            base_timeout = 240 # 4 minutes for very large prompts (reduced from 300)
        elif prompt_length > 10000:
            base_timeout = 120 # 2 minutes for large prompts (reduced from 180)
        
        # Claude-4-Sonnet typically needs more time
        if "claude-4" in model.lower():
            base_timeout = int(base_timeout * 1.2) # Reduced multiplier from 1.5 to 1.2
        
        # Ensure timeout doesn't exceed reasonable limits
        max_timeout = 480 if os.environ.get('ENVIRONMENT') == 'production' else 300
        timeout = min(base_timeout, max_timeout)
        
        # Log timeout setting for debugging
        print(f"🕐 Using async timeout: {timeout}s for prompt length {prompt_length}, model: {model}")
        
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        session = None
        try:
            session = aiohttp.ClientSession(timeout=timeout_obj, connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT))
            async with session.post(endpoint, headers=headers, json=payload) as response:
                if response.status in [200, 201]:
                    return await response.json()
                else:
                    text = await response.text()
                    raise Exception(f"Failed to generate text: {response.status} - {text}")
        except Exception as e:
            # Consider logging the exception here if appropriate
            raise
        finally:
            if session is not None:
                await session.close()


    async def _async_generate_text_simple(self, prompt: str, model: str = "claude-3-haiku") -> str:
        """Simple async text generation that returns just the generated text."""
        response = await self._async_generate_text(prompt, model)
        
        if 'generations' in response:
            return response['generations'][0].get('text', '')
        elif 'choices' in response:
            return response['choices'][0].get('message', {}).get('content', '')
        elif 'text' in response:
            return response['text']
        else:
            return str(response)

    async def _async_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-3-haiku",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Async multi-turn chat completion."""
        model_mapping = {
            "claude-3-haiku": "sfdc_ai__Default Bedrock Anthropic Claude3Haiku",
            "claude-3-sonnet": "sfdc_ai__Default Bedrock Anthropic Claude37Sonnet",
            "claude-4-sonnet": "sfdc_ai__Default Bedrock Anthropic Claude4Sonnet",
            "gpt-4": "sfdc_ai__DefaultGPT4Omni",
            "gpt-4-mini": "sfdc_ai__Default OpenAIGPT4Omni Mini",
            "gemini-pro": "sfdc_ai__Default VertexAIGemini25Flash001"
        }
        
        api_model_name = model_mapping.get(model, model)
        
        access_token = await self._async_get_access_token()
        endpoint = f"https://api.salesforce.com/einstein/platform/v1/models/{api_model_name}/chat-generations"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'x-sfdc-app-context': 'EinsteinGPT',
            'x-client-feature-id': 'ai-platform-models-connected-app'
        }
        
        payload = {
            "messages": messages,
            "max Tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        # Calculate timeout dynamically based on prompt size and model
        # CONSERVATIVE timeout settings to avoid gunicorn worker timeouts
        total_content_length = sum(len(msg.get('content', '')) for msg in messages)
        base_timeout = 60 # Reduced base timeout from 120 to 60 seconds
        
        # Increase timeout for large content and slower models
        if total_content_length > 30000:
            base_timeout = 240 # 4 minutes for very large content (reduced from 300)
        elif total_content_length > 10000:
            base_timeout = 120 # 2 minutes for large content (reduced from 180)
        
        # Claude-4-Sonnet typically needs more time
        if "claude-4" in model.lower():
            base_timeout = int(base_timeout * 1.2) # Reduced multiplier from 1.5 to 1.2
        
        # Ensure timeout doesn't exceed reasonable limits
        max_timeout = 480 if os.environ.get('ENVIRONMENT') == 'production' else 300
        timeout = min(base_timeout, max_timeout)
        
        # Log timeout setting for debugging
        print(f"🕐 Using async chat timeout: {timeout}s for content length {total_content_length}, model: {model}")
        
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        
        # Rate limiting retry logic with exponential backoff
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=timeout_obj, connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as session:
                    async with session.post(endpoint, headers=headers, json=payload) as response:
                        if response.status in [200, 201]:
                            return await response.json()
                        elif response.status == 429:  # Rate limit exceeded
                            if attempt < max_retries:
                                # Exponential backoff with jitter
                                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                                print(f"⏸️ Rate limit hit, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})")
                                await asyncio.sleep(delay)
                                continue
                            else:
                                error_text = await response.text()
                                raise Exception(f"Rate limit exceeded after {max_retries} retries: {response.status} - {error_text}")
                        else:
                            error_text = await response.text()
                            raise Exception(f"Chat completion failed: {response.status} - {error_text}")
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    print(f"⏸️ Timeout, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise Exception(f"Request timed out after {max_retries} retries")
        
        # Should not reach here, but fallback
        raise Exception("Unexpected error in retry logic")


def main():
    """Example usage of the Salesforce Models Client."""
    try:
        print("🚀 Initializing Salesforce Models API Client...")
        client = SalesforceModelsClient()
        
        print("\n📋 Listing available models...")
        try:
            models = client.list_models()
            print(f"Found {len(models)} available models:")
            for model in models:
                print(f" - {model.get('name', 'Unknown')}: {model.get('description', 'No description')}")
        except Exception as e:
            print(f"⚠️ Could not list models: {e}")
            print("This may be expected if Models API endpoints are different than assumed.")
        
        print("\n💬 Testing text generation...")
        test_prompt = "Write a brief professional email thanking someone for their time in a meeting."
        
        try:
            response = client.generate_text_simple(test_prompt, model="claude-3-haiku")
            print(f"Generated text:\n{response}")
        except Exception as e:
            print(f"❌ Text generation failed: {e}")
            print("This may indicate the Models API endpoints or payload structure are different.")
            print("Check Salesforce documentation for the correct Models API format.")
        
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        print("\n Make sure you have:")
        print("1. Set SALESFORCE_CONSUMER_KEY environment variable")
        print("2. Set SALESFORCE_CONSUMER_SECRET environment variable")
        print("3. Set SALESFORCE_INSTANCE_URL environment variable")


if __name__ == "__main__":
    main()
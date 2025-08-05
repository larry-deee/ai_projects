#!/usr/bin/env python3
"""
Salesforce Models API Command Line Interface
============================================

A command-line tool for interacting with Salesforce/Agentforce hosted LLMs.

Usage:
    python cli.py generate "Write a haiku about AI"
    python cli.py generate "Explain quantum computing" --model gpt-4
    python cli.py models
    python cli.py chat
"""

import sys
import os
import json
import argparse
from salesforce_models_client import SalesforceModelsClient


def get_config_path(args):
    """Auto-detect config.json if no config specified."""
    config_path = args.config
    if not config_path:
        if os.path.exists('config.json'):
            config_path = 'config.json'
        elif os.path.exists('../config.json'):
            config_path = '../config.json'
    return config_path


def cmd_generate(args):
    """Generate text using specified model."""
    try:
        client = SalesforceModelsClient(get_config_path(args))
        
        print(f"🤖 Generating text using {args.model}...")
        print(f"📝 Prompt: {args.prompt}")
        print("-" * 50)
        
        if args.system:
            response = client.generate_text(
                prompt=args.prompt,
                model=args.model,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                system_message=args.system
            )
        else:
            response = client.generate_text(
                prompt=args.prompt,
                model=args.model,
                max_tokens=args.max_tokens,
                temperature=args.temperature
            )
        
        # Extract the generated text
        if 'generation' in response and 'generated Text' in response['generation']:
            generated_text = response['generation']['generated Text']
            print(f"✨ Generated Text:\n{generated_text}")
            
            if args.verbose:
                print(f"\n📊 Metadata:")
                if 'parameters' in response and 'usage' in response['parameters']:
                    usage = response['parameters']['usage']
                    print(f"    Input tokens: {usage.get('input Token Count', 'N/A')}")
                    print(f"    Output tokens: {usage.get('output Token Count', 'N/A')}")
                    print(f"    Total tokens: {usage.get('total Token Count', 'N/A')}")
                    print(f"    Model: {response.get('parameters', {}).get('model', 'N/A')}")
        else:
            print(f"✨ Raw Response:\n{json.dumps(response, indent=2)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def cmd_models(args):
    """List available models with usage examples."""
    try:
        client = SalesforceModelsClient(get_config_path(args))
        models = client.list_models()
        
        print("📋 Available Models & Usage Examples:")
        print("=" * 60)
        
        # Create friendly name mapping
        friendly_names = {
            "sfdc_ai__Default Bedrock Anthropic Claude3Haiku": "claude-3-haiku",
            "sfdc_ai__Default Bedrock Anthropic Claude37Sonnet": "claude-3-sonnet", 
            "sfdc_ai__Default Bedrock Anthropic Claude4Sonnet": "claude-4-sonnet",
            "sfdc_ai__Default OpenAIGPT4Omni Mini": "gpt-4-mini",
            "sfdc_ai__DefaultGPT4Omni": "gpt-4",
            "sfdc_ai__Default VertexAIGemini25Flash001": "gemini-pro"
        }
        
        for i, model in enumerate(models, 1):
            friendly_name = friendly_names.get(model['name'], model['name'])
            
            print(f"{i}. 🤖 {model['display_name']}")
            print(f"    Provider: {model['provider']}")
            print(f"    Description: {model['description']}")
            print(f"    Friendly Name: {friendly_name}")
            print(f"    💡 CLI Usage Examples:")
            print(f"    python cli.py generate \"Write a haiku\" --model {friendly_name}")
            print(f"    python cli.py sentiment \"Great product!\" --model {friendly_name}")
            print(f"    python cli.py chat --model {friendly_name}")
            print(f"    ./sf-ai generate \"Explain AI\" --model {friendly_name}")
            print()
        
        print("🎯 Quick Reference:")
        print("    • Default model: claude-3-haiku (fast, efficient)")
        print("    • Best for reasoning: gpt-4 (slower, more capable)")
        print("    • Balanced option: claude-3-sonnet")
        print("    • Fastest: gemini-pro")
        print()
        print("📖 More Examples:")
        print("    python cli.py generate \"Write code\" --model gpt-4 --max-tokens 500")
        print("    python cli.py generate \"Be creative\" --model claude-4-sonnet --temperature 0.9")
        print("    python cli.py sentiment \"Mixed feelings\" --model claude-3-haiku")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def cmd_chat(args):
    """Interactive chat mode."""
    try:
        client = SalesforceModelsClient(get_config_path(args))
        
        print(f"💬 Interactive Chat Mode - {args.model}")
        print("=" * 50)
        print("Type 'quit' or 'exit' to end the conversation")
        print("Type 'clear' to start a new conversation")
        print()
        
        conversation = []
        if args.system:
            conversation.append({"role": "system", "content": args.system})
            print(f"🎯 System message set: {args.system[:50]}...")
            print()
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() == 'clear':
                    conversation = []
                    if args.system:
                        conversation.append({"role": "system", "content": args.system})
                    print("🗑️ Conversation cleared!")
                    continue
                
                if not user_input:
                    continue
                
                conversation.append({"role": "user", "content": user_input})
                
                print(f"🤖 {args.model}: ", end="", flush=True)
                
                # Convert conversation to a single prompt for the working API
                conversation_text = ""
                for msg in conversation:
                    if msg["role"] == "system":
                        conversation_text += f"System: {msg['content']}\n\n"
                    elif msg["role"] == "user":
                        conversation_text += f"User: {msg['content']}\n\n"
                    elif msg["role"] == "assistant":
                        conversation_text += f"Assistant: {msg['content']}\n\n"
                
                # Add the instruction for the assistant to respond
                conversation_text += "Assistant:"
                
                response = client.generate_text(
                    prompt=conversation_text,
                    model=args.model,
                    max_tokens=args.max_tokens,
                    temperature=args.temperature
                )
                
                # Extract generated text
                generated_text = "No response generated"
                if 'generation' in response and 'generated Text' in response['generation']:
                    generated_text = response['generation']['generated Text'].strip()
                elif isinstance(response, dict) and 'text' in response:
                    generated_text = response['text'].strip()
                else:
                    # Debug: print the actual response structure
                    print(f"\n🔍 Debug - Response structure: {list(response.keys()) if isinstance(response, dict) else type(response)}")
                    generated_text = str(response)[:200] + "..." if len(str(response)) > 200 else str(response)
                
                # Clean up the response text - remove leading "Assistant:" if present
                if generated_text.startswith("Assistant:"):
                    generated_text = generated_text[10:].strip()
                
                print(generated_text)
                conversation.append({"role": "assistant", "content": generated_text})
                print()
                
            except KeyboardInterrupt:
                print("\n👋 Chat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error in chat: {e}")
        
    except Exception as e:
        print(f"❌ Error starting chat: {e}")
        sys.exit(1)


def cmd_sentiment(args):
    """Analyze sentiment of text."""
    try:
        client = SalesforceModelsClient(get_config_path(args))
        
        system_prompt = """Analyze the sentiment of the given text and respond with JSON:
{
    "sentiment": "positive|negative|neutral",
    "confidence": 0.95,
    "score": 0.8,
    "emotion": "joy|anger|fear|sadness|surprise|disgust|trust|anticipation",
    "intensity": 0.7,
    "explanation": "Brief explanation"
}"""
        
        print(f"😊 Analyzing sentiment...")
        print(f"📝 Text: {args.text}")
        print("-" * 50)
        
        response = client.generate_text(
            prompt=f"Analyze the sentiment of this text: {args.text}",
            system_message=system_prompt,
            model=args.model,
            temperature=0.1, # Low temperature for consistent analysis
            max_tokens=300
        )
        
        if 'generation' in response and 'generated Text' in response['generation']:
            generated_text = response['generation']['generated Text']
            print(f"🎯 Sentiment Analysis:\n{generated_text}")
        else:
            print(f"🎯 Raw Response:\n{json.dumps(response, indent=2)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Salesforce Models API Command Line Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🎯 Command Examples:

Basic Usage:
    python cli.py models # List all available models
    python cli.py generate "Write a professional email" # Generate with default model
    python cli.py sentiment "I love this product!" # Analyze sentiment
    python cli.py chat # Start interactive chat
    
Model Selection:
    python cli.py generate "Explain AI" --model gpt-4 # Use GPT-4
    python cli.py generate "Write code" --model claude-3-sonnet # Use Claude Sonnet 
    python cli.py generate "Be creative" --model gemini-pro # Use Gemini
    python cli.py sentiment "Mixed feelings" --model claude-3-haiku # Haiku for sentiment
    
Parameter Examples:
    python cli.py generate "Write a story" --max-tokens 500 # Limit output length
    python cli.py generate "Be creative" --temperature 0.9 # More creative (0.0-1.0)
    python cli.py generate "Be precise" --temperature 0.1 # More focused
    python cli.py generate "You are a poet" --system "Write a sonnet" # With system message
    
Configuration:
    python cli.py generate "Hello" --config config.json # Use config file
    ./sf-ai generate "Quick test" # Use shell wrapper
    
Available Models:
    • claude-3-haiku (fast, efficient - default)
    • claude-3-sonnet (balanced, good reasoning) 
    • claude-4-sonnet (latest, most capable)
    • gpt-4 (excellent reasoning)
    • gpt-4-mini (compact, efficient)
    • gemini-pro (fast, multimodal)
    """
    )
    
    # Global arguments
    parser.add_argument('--config', '-c', help='Path to config.json file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate text using AI models')
    gen_parser.add_argument('prompt', help='Text prompt to generate from (e.g., "Write a poem")')
    gen_parser.add_argument('--model', '-m', default='claude-3-haiku', 
                            help='Model: claude-3-haiku, gpt-4, claude-3-sonnet, gemini-pro, etc. (default: claude-3-haiku)')
    gen_parser.add_argument('--max-tokens', '-t', type=int, default=1000,
                            help='Max output length: 50-2000 tokens (default: 1000)')
    gen_parser.add_argument('--temperature', '-T', type=float, default=0.7,
                            help='Creativity: 0.0=focused, 1.0=creative (default: 0.7)')
    gen_parser.add_argument('--system', '-s', help='System message: "You are a helpful assistant"')
    
    # Models command
    models_parser = subparsers.add_parser('models', help='List available models with usage examples')
    
    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Start interactive chat conversation')
    chat_parser.add_argument('--model', '-m', default='claude-3-haiku',
                             help='Model: claude-3-haiku, gpt-4, etc. (default: claude-3-haiku)')
    chat_parser.add_argument('--max-tokens', '-t', type=int, default=1000,
                             help='Max tokens per response: 50-2000 (default: 1000)')
    chat_parser.add_argument('--temperature', '-T', type=float, default=0.7,
                             help='Creativity: 0.0=focused, 1.0=creative (default: 0.7)')
    chat_parser.add_argument('--system', '-s', help='System role: "You are a coding assistant"')
    
    # Sentiment command
    sentiment_parser = subparsers.add_parser('sentiment', help='Analyze text sentiment and emotions')
    sentiment_parser.add_argument('text', help='Text to analyze (e.g., "I love this!")')
    sentiment_parser.add_argument('--model', '-m', default='claude-3-haiku',
                                  help='Model: claude-3-haiku, gpt-4, etc. (default: claude-3-haiku)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Route to appropriate command
    if args.command == 'generate':
        cmd_generate(args)
    elif args.command == 'models':
        cmd_models(args)
    elif args.command == 'chat':
        cmd_chat(args)
    elif args.command == 'sentiment':
        cmd_sentiment(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
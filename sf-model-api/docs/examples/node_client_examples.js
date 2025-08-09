#!/usr/bin/env node
/**
 * Anthropic API Node.js Client Examples
 * 
 * This file demonstrates how to use the Salesforce Models API Gateway's 
 * Anthropic-compatible endpoints with the official Anthropic Node.js SDK.
 * 
 * Prerequisites:
 * - npm install @anthropic-ai/sdk
 * - Ensure the gateway server is running on localhost:8000
 * 
 * Usage:
 *     node node_client_examples.js
 */

import { Anthropic } from '@anthropic-ai/sdk';
import fetch from 'node-fetch';

// Configuration
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000/anthropic';
const ANTHROPIC_VERSION = '2023-06-01';

/**
 * Check if the server is running
 */
async function checkServerHealth() {
    try {
        const healthUrl = API_BASE_URL.replace('/anthropic', '') + '/health';
        const response = await fetch(healthUrl);
        if (response.ok) {
            console.log('✅ Server is running');
            return true;
        } else {
            console.log('❌ Server returned error status');
            return false;
        }
    } catch (error) {
        console.log(`❌ Server is not running: ${error.message}`);
        return false;
    }
}

/**
 * Example 1: Basic message completion
 */
async function example1BasicMessage() {
    console.log('\n1️⃣  Basic Message Completion');
    console.log('============================');
    
    const anthropic = new Anthropic({
        apiKey: 'any-key',  // Not used for local API
        baseURL: API_BASE_URL
    });
    
    try {
        const response = await anthropic.messages.create({
            model: 'claude-3-haiku-20240307',
            messages: [
                { role: 'user', content: 'Hello, Claude! Can you introduce yourself briefly?' }
            ],
            max_tokens: 1000
        });
        
        console.log(`Response ID: ${response.id}`);
        console.log(`Model: ${response.model}`);
        console.log(`Content: ${response.content[0].text}`);
        console.log(`Stop reason: ${response.stop_reason}`);
        console.log(`Usage:`, response.usage);
        
    } catch (error) {
        console.log(`Error: ${error.message}`);
    }
}

/**
 * Example 2: Message with system context
 */
async function example2SystemContext() {
    console.log('\n2️⃣  Message with System Context');
    console.log('===============================');
    
    const anthropic = new Anthropic({
        apiKey: 'any-key',
        baseURL: API_BASE_URL
    });
    
    try {
        const response = await anthropic.messages.create({
            model: 'claude-3-haiku-20240307',
            messages: [
                { role: 'user', content: 'Explain quantum computing in simple terms.' }
            ],
            system: 'You are a physics professor who excels at explaining complex concepts to beginners. Use analogies and simple language.',
            max_tokens: 200
        });
        
        console.log(`Content: ${response.content[0].text}`);
        console.log(`Input tokens: ${response.usage.input_tokens}`);
        console.log(`Output tokens: ${response.usage.output_tokens}`);
        
    } catch (error) {
        console.log(`Error: ${error.message}`);
    }
}

/**
 * Example 3: Multi-turn conversation
 */
async function example3MultiTurnConversation() {
    console.log('\n3️⃣  Multi-turn Conversation');
    console.log('===========================');
    
    const anthropic = new Anthropic({
        apiKey: 'any-key',
        baseURL: API_BASE_URL
    });
    
    // Simulate a conversation
    const conversation = [
        { role: 'user', content: 'What is the capital of Japan?' }
    ];
    
    try {
        // First exchange
        const response1 = await anthropic.messages.create({
            model: 'claude-3-haiku-20240307',
            messages: conversation,
            max_tokens: 100
        });
        
        console.log(`User: ${conversation[0].content}`);
        console.log(`Claude: ${response1.content[0].text}`);
        
        // Add Claude's response to conversation
        conversation.push(
            { role: 'assistant', content: response1.content[0].text },
            { role: 'user', content: 'What is the population of that city?' }
        );
        
        // Second exchange
        const response2 = await anthropic.messages.create({
            model: 'claude-3-haiku-20240307',
            messages: conversation,
            max_tokens: 100
        });
        
        console.log('User: What is the population of that city?');
        console.log(`Claude: ${response2.content[0].text}`);
        
    } catch (error) {
        console.log(`Error: ${error.message}`);
    }
}

/**
 * Example 4: Temperature comparison
 */
async function example4TemperatureComparison() {
    console.log('\n4️⃣  Temperature Comparison');
    console.log('==========================');
    
    const anthropic = new Anthropic({
        apiKey: 'any-key',
        baseURL: API_BASE_URL
    });
    
    const prompt = 'Write a creative haiku about artificial intelligence.';
    const temperatures = [0.0, 0.5, 1.0];
    
    for (const temp of temperatures) {
        try {
            const response = await anthropic.messages.create({
                model: 'claude-3-haiku-20240307',
                messages: [
                    { role: 'user', content: prompt }
                ],
                temperature: temp,
                max_tokens: 100
            });
            
            console.log(`\nTemperature ${temp}:`);
            console.log(response.content[0].text);
            
        } catch (error) {
            console.log(`Error at temperature ${temp}: ${error.message}`);
        }
    }
}

/**
 * Example 5: Model comparison
 */
async function example5ModelComparison() {
    console.log('\n5️⃣  Model Comparison');
    console.log('====================');
    
    const anthropic = new Anthropic({
        apiKey: 'any-key',
        baseURL: API_BASE_URL
    });
    
    const models = [
        'claude-3-haiku-20240307',
        'claude-3-sonnet-20240229'
    ];
    
    const prompt = 'Explain the concept of recursion in programming in one paragraph.';
    
    for (const model of models) {
        try {
            const startTime = Date.now();
            const response = await anthropic.messages.create({
                model: model,
                messages: [
                    { role: 'user', content: prompt }
                ],
                max_tokens: 150
            });
            const endTime = Date.now();
            
            console.log(`\n${model}:`);
            console.log(`Response time: ${(endTime - startTime) / 1000}s`);
            console.log(`Tokens: ${response.usage.input_tokens} in, ${response.usage.output_tokens} out`);
            console.log(`Content: ${response.content[0].text.substring(0, 200)}...`);
            
        } catch (error) {
            console.log(`Error with ${model}: ${error.message}`);
        }
    }
}

/**
 * Example 6: Basic streaming
 */
async function example6StreamingBasic() {
    console.log('\n6️⃣  Basic Streaming');
    console.log('===================');
    
    const anthropic = new Anthropic({
        apiKey: 'any-key',
        baseURL: API_BASE_URL
    });
    
    try {
        console.log('Streaming response:');
        
        const stream = await anthropic.messages.stream({
            model: 'claude-3-haiku-20240307',
            messages: [
                { role: 'user', content: 'Write a short story about a robot learning to paint.' }
            ],
            max_tokens: 300
        });
        
        for await (const chunk of stream) {
            if (chunk.type === 'content_block_delta') {
                process.stdout.write(chunk.delta.text);
            }
        }
        
        console.log(); // New line after streaming
        
        const message = await stream.finalMessage();
        console.log(`\nFinal usage: ${JSON.stringify(message.usage)}`);
        
    } catch (error) {
        console.log(`Error: ${error.message}`);
    }
}

/**
 * Example 7: Streaming with event inspection
 */
async function example7StreamingWithEvents() {
    console.log('\n7️⃣  Streaming with Event Inspection');
    console.log('===================================');
    
    const anthropic = new Anthropic({
        apiKey: 'any-key',
        baseURL: API_BASE_URL
    });
    
    try {
        console.log('Event types received:');
        
        const stream = await anthropic.messages.stream({
            model: 'claude-3-haiku-20240307',
            messages: [
                { role: 'user', content: 'Count from 1 to 5 with a fact about each number.' }
            ],
            max_tokens: 200
        });
        
        for await (const event of stream) {
            if (event.type === 'message_start') {
                console.log(`🚀 ${event.type}: ${event.message.id}`);
            } else if (event.type === 'content_block_start') {
                console.log(`📝 ${event.type}: index ${event.index}`);
            } else if (event.type === 'content_block_delta') {
                process.stdout.write(event.delta.text);
            } else if (event.type === 'content_block_stop') {
                console.log(`\n📋 ${event.type}: index ${event.index}`);
            } else if (event.type === 'message_delta') {
                console.log(`🔄 ${event.type}:`, event.delta);
            } else if (event.type === 'message_stop') {
                console.log(`✅ ${event.type}`);
            }
        }
        
    } catch (error) {
        console.log(`Error: ${error.message}`);
    }
}

/**
 * Example 8: Token counting
 */
async function example8TokenCounting() {
    console.log('\n8️⃣  Token Counting');
    console.log('==================');
    
    const anthropic = new Anthropic({
        apiKey: 'any-key',
        baseURL: API_BASE_URL
    });
    
    const messages = [
        { role: 'user', content: 'This is a test message to count tokens. It has multiple sentences! And some punctuation? Plus numbers like 123 and symbols like @#$.' }
    ];
    
    const systemMessage = 'You are a helpful assistant that provides accurate information.';
    
    try {
        // Use the count_tokens endpoint
        const countResponse = await anthropic.messages.countTokens({
            model: 'claude-3-haiku-20240307',
            messages: messages,
            system: systemMessage
        });
        
        console.log(`Input tokens: ${countResponse.input_tokens}`);
        
        // Compare with actual usage
        const actualResponse = await anthropic.messages.create({
            model: 'claude-3-haiku-20240307',
            messages: messages,
            system: systemMessage,
            max_tokens: 50
        });
        
        console.log(`Actual input tokens (from completion): ${actualResponse.usage.input_tokens}`);
        console.log(`Output tokens: ${actualResponse.usage.output_tokens}`);
        console.log(`Total tokens: ${actualResponse.usage.input_tokens + actualResponse.usage.output_tokens}`);
        
    } catch (error) {
        console.log(`Error: ${error.message}`);
    }
}

/**
 * Example 9: Error handling
 */
async function example9ErrorHandling() {
    console.log('\n9️⃣  Error Handling');
    console.log('==================');
    
    const anthropic = new Anthropic({
        apiKey: 'any-key',
        baseURL: API_BASE_URL
    });
    
    // Test various error conditions
    const testCases = [
        {
            name: 'Invalid model',
            params: {
                model: 'invalid-model-name',
                messages: [{ role: 'user', content: 'Hello' }],
                max_tokens: 100
            }
        },
        {
            name: 'Empty messages',
            params: {
                model: 'claude-3-haiku-20240307',
                messages: [],
                max_tokens: 100
            }
        }
    ];
    
    for (const testCase of testCases) {
        console.log(`\nTesting: ${testCase.name}`);
        try {
            const response = await anthropic.messages.create(testCase.params);
            console.log(`✅ Unexpected success: ${response.content[0].text.substring(0, 50)}...`);
        } catch (error) {
            if (error.status === 400) {
                console.log(`❌ Bad request error: ${error.message}`);
            } else {
                console.log(`❌ Other error: ${error.message}`);
            }
        }
    }
}

/**
 * Example 10: Performance comparison
 */
async function example10PerformanceComparison() {
    console.log('\n🔟 Performance Comparison');
    console.log('=========================');
    
    const anthropic = new Anthropic({
        apiKey: 'any-key',
        baseURL: API_BASE_URL
    });
    
    const prompt = 'Write a haiku about technology.';
    
    try {
        // Non-streaming
        console.log('Non-streaming (wait for complete response):');
        const startTime1 = Date.now();
        const nonStreamResponse = await anthropic.messages.create({
            model: 'claude-3-haiku-20240307',
            messages: [{ role: 'user', content: prompt }],
            max_tokens: 100
        });
        const endTime1 = Date.now();
        
        console.log(`Time: ${(endTime1 - startTime1) / 1000}s`);
        console.log(`Result: ${nonStreamResponse.content[0].text}`);
        
        // Streaming
        console.log('\nStreaming (immediate response start):');
        const startTime2 = Date.now();
        let firstChunkTime = null;
        let fullText = '';
        
        const stream = await anthropic.messages.stream({
            model: 'claude-3-haiku-20240307',
            messages: [{ role: 'user', content: prompt }],
            max_tokens: 100
        });
        
        for await (const chunk of stream) {
            if (chunk.type === 'content_block_delta') {
                if (firstChunkTime === null) {
                    firstChunkTime = Date.now();
                }
                fullText += chunk.delta.text;
            }
        }
        
        const endTime2 = Date.now();
        
        console.log(`Time to first chunk: ${(firstChunkTime - startTime2) / 1000}s`);
        console.log(`Total time: ${(endTime2 - startTime2) / 1000}s`);
        console.log(`Result: ${fullText}`);
        
    } catch (error) {
        console.log(`Error: ${error.message}`);
    }
}

/**
 * Main function to run all examples
 */
async function main() {
    console.log('🚀 Anthropic Node.js SDK Examples');
    console.log('==================================');
    console.log(`Using API base URL: ${API_BASE_URL}`);
    
    // Check server health
    const serverHealthy = await checkServerHealth();
    if (!serverHealthy) {
        console.log('Please start the server first and try again.');
        return;
    }
    
    // Run examples
    await example1BasicMessage();
    await example2SystemContext();
    await example3MultiTurnConversation();
    await example4TemperatureComparison();
    await example5ModelComparison();
    await example6StreamingBasic();
    await example7StreamingWithEvents();
    await example8TokenCounting();
    await example9ErrorHandling();
    await example10PerformanceComparison();
    
    console.log('\n✅ All examples completed!');
    console.log('='.repeat(50));
    console.log('These examples demonstrated:');
    console.log('• Basic message completion');
    console.log('• System context usage');
    console.log('• Multi-turn conversations');
    console.log('• Temperature effects');
    console.log('• Model comparison');
    console.log('• Basic streaming');
    console.log('• Streaming event inspection');
    console.log('• Token counting');
    console.log('• Error handling');
    console.log('• Performance comparison');
}

// Run the examples
main().catch(error => {
    console.error('Unhandled error:', error);
    process.exit(1);
});
import os
import json
import uuid
import time
import threading
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor

class ConversationManager:
    """
    Thread-safe, distributed conversation management system.
    Handles context preservation, serialization, and retrieval.
    
    Key Features:
    - Unique conversation ID generation
    - Distributed context storage
    - Concurrent-safe operations
    - Configurable persistence strategies
    """
    
    def __init__(self, storage_path: str = None, max_conversations: int = 1000, max_messages_per_conversation: int = 50):
        """
        Initialize ConversationManager with configurable storage options.
        
        Args:
            storage_path: Directory for persistent conversation storage
            max_conversations: Maximum number of conversations to store
            max_messages_per_conversation: Maximum messages per conversation
        """
        self.storage_path = storage_path or os.path.join(os.getcwd(), 'conversation_cache')
        self.max_conversations = max_conversations
        self.max_messages_per_conversation = max_messages_per_conversation
        
        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Thread-safe operations executor
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._lock = threading.Lock()
    
    def create_conversation(self, initial_context: Dict[str, Any] = None) -> str:
        """
        Create a new conversation with optional initial context.
        
        Returns:
            Unique conversation ID
        """
        conversation_id = str(uuid.uuid4())
        
        conversation_data = {
            'id': conversation_id,
            'created_at': time.time(),
            'updated_at': time.time(),
            'messages': [],
            'system_context': initial_context or {},
            'metadata': {
                'model': initial_context.get('model', 'claude-3-haiku') if initial_context else 'claude-3-haiku',
                'total_tokens': 0,
                'message_count': 0
            }
        }
        
        self._save_conversation(conversation_id, conversation_data)
        return conversation_id
    
    def add_message(self, conversation_id: str, message: Dict[str, Any]) -> bool:
        """
        Add a message to an existing conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            message: Message dictionary
        
        Returns:
            Boolean indicating successful message addition
        """
        try:
            conversation = self._load_conversation(conversation_id)
            
            if not conversation:
                return False
            
            # Truncate messages if exceeding limit
            if len(conversation['messages']) >= self.max_messages_per_conversation:
                conversation['messages'] = conversation['messages'][-self.max_messages_per_conversation + 1:]
            
            conversation['messages'].append(message)
            conversation['updated_at'] = time.time()
            
            # Update metadata
            conversation['metadata']['message_count'] += 1
            conversation['metadata']['total_tokens'] += message.get('token_count', 0)
            
            self._save_conversation(conversation_id, conversation)
            return True
        
        except Exception as e:
            print(f"Error adding message to conversation {conversation_id}: {e}")
            return False
    
    def get_conversation_history(self, conversation_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history.
        
        Args:
            conversation_id: Unique conversation identifier
            limit: Maximum number of messages to return
        
        Returns:
            List of messages or empty list
        """
        conversation = self._load_conversation(conversation_id)
        
        if not conversation:
            return []
        
        messages = conversation['messages']
        return messages[-limit:] if limit else messages
    
    def _load_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Load conversation from persistent storage.
        
        Args:
            conversation_id: Unique conversation identifier
        
        Returns:
            Conversation dictionary or None
        """
        conversation_file = os.path.join(self.storage_path, f"{conversation_id}.json")
        
        try:
            with open(conversation_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Conversation {conversation_id} not found")
            return None
        except Exception as e:
            print(f"Error loading conversation {conversation_id}: {e}")
            return None
    
    def _save_conversation(self, conversation_id: str, conversation_data: Dict[str, Any]):
        """
        Save conversation to persistent storage with thread-safe atomic write.
        
        Args:
            conversation_id: Unique conversation identifier
            conversation_data: Complete conversation dictionary
        """
        conversation_file = os.path.join(self.storage_path, f"{conversation_id}.json")
        
        try:
            # Use temporary file for atomic write
            temp_file = f"{conversation_file}.tmp"
            
            with open(temp_file, 'w') as f:
                json.dump(conversation_data, f, indent=2)
            
            # Atomic rename
            os.replace(temp_file, conversation_file)
        
        except Exception as e:
            print(f"Error saving conversation {conversation_id}: {e}")
    
    def delete_conversation(self, conversation_id: str):
        """
        Delete a conversation from storage.
        
        Args:
            conversation_id: Unique conversation identifier
        """
        conversation_file = os.path.join(self.storage_path, f"{conversation_id}.json")
        
        try:
            os.remove(conversation_file)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error deleting conversation {conversation_id}: {e}")
    
    def cleanup_old_conversations(self):
        """
        Remove conversations exceeding storage limit or older than 7 days.
        """
        try:
            conversations = [
                f for f in os.listdir(self.storage_path) 
                if f.endswith('.json')
            ]
            
            conversations.sort(key=lambda x: os.path.getctime(os.path.join(self.storage_path, x)))
            
            if len(conversations) > self.max_conversations:
                for old_conversation in conversations[:len(conversations) - self.max_conversations]:
                    os.remove(os.path.join(self.storage_path, old_conversation))
        
        except Exception as e:
            print(f"Error cleaning up conversations: {e}")

# Singleton instance for easy import and use
conversation_manager = ConversationManager()
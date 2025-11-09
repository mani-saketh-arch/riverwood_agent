import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class MemoryService:
    def __init__(self, data_file: str = "data/conversations.json"):
        self.data_file = data_file
        self._ensure_data_file()
    
    def _ensure_data_file(self):
        """Create data directory and file if they don't exist"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w') as f:
                json.dump({}, f)
    
    def get_conversation_history(self, phone_number: str) -> List[Dict]:
        """Get conversation history for a customer"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                return data.get(phone_number, {}).get("history", [])
        except Exception as e:
            print(f"Error reading conversation history: {e}")
            return []
    
    def save_conversation(self, phone_number: str, user_message: str, ai_response: str, language: str = None):
        """Save a conversation turn"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            if phone_number not in data:
                data[phone_number] = {
                    "customer_name": "Unknown",
                    "preferred_language": language or "English",
                    "first_contact": datetime.now().isoformat(),
                    "history": []
                }
            
            # Update language preference if provided
            if language:
                data[phone_number]["preferred_language"] = language
            
            data[phone_number]["history"].append({
                "timestamp": datetime.now().isoformat(),
                "user": user_message,
                "assistant": ai_response
            })
            
            # Keep only last 10 conversations to manage file size
            if len(data[phone_number]["history"]) > 10:
                data[phone_number]["history"] = data[phone_number]["history"][-10:]
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving conversation: {e}")
    
    def get_customer_info(self, phone_number: str) -> Optional[Dict]:
        """Get customer information"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                return data.get(phone_number)
        except Exception as e:
            print(f"Error getting customer info: {e}")
            return None
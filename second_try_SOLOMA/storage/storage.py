"""
Storage module for managing user violations, message history, and ban information
Uses JSON for simplicity
"""
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from config.settings import STORAGE_PATH


class Storage:
    """Simple JSON-based storage"""
    
    def __init__(self, storage_path: str = STORAGE_PATH):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        
        self.violations_file = os.path.join(storage_path, "violations.json")
        self.bans_file = os.path.join(storage_path, "bans.json")
        self.messages_file = os.path.join(storage_path, "messages.json")
        
        # Initialize files if they don't exist
        self._ensure_files()

    def _ensure_files(self):
        """Create empty files if they don't exist"""
        for file_path in [self.violations_file, self.bans_file, self.messages_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)

    def _load_json(self, file_path: str) -> dict:
        """Load JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return {}

    def _save_json(self, file_path: str, data: dict):
        """Save JSON file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving {file_path}: {e}")

    # Violations management
    def add_violation(self, user_id: int, category: str, reason: str) -> int:
        """Add violation for user, return violation count"""
        violations = self._load_json(self.violations_file)
        user_id_str = str(user_id)
        
        if user_id_str not in violations:
            violations[user_id_str] = []
        
        violations[user_id_str].append({
            "category": category,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_json(self.violations_file, violations)
        return len(violations[user_id_str])

    def get_violation_count(self, user_id: int) -> int:
        """Get total violations for user"""
        violations = self._load_json(self.violations_file)
        user_id_str = str(user_id)
        
        if user_id_str not in violations:
            return 0
        
        return len(violations[user_id_str])

    def get_violations(self, user_id: int) -> List[Dict]:
        """Get all violations for user"""
        violations = self._load_json(self.violations_file)
        user_id_str = str(user_id)
        
        return violations.get(user_id_str, [])

    def clear_violations(self, user_id: int):
        """Clear all violations for user"""
        violations = self._load_json(self.violations_file)
        user_id_str = str(user_id)
        
        if user_id_str in violations:
            del violations[user_id_str]
            self._save_json(self.violations_file, violations)

    # Ban management
    def ban_user(self, user_id: int, reason: str = ""):
        """Ban user"""
        bans = self._load_json(self.bans_file)
        user_id_str = str(user_id)
        
        bans[user_id_str] = {
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
        self._save_json(self.bans_file, bans)

    def unban_user(self, user_id: int):
        """Unban user"""
        bans = self._load_json(self.bans_file)
        user_id_str = str(user_id)
        
        if user_id_str in bans:
            del bans[user_id_str]
            self._save_json(self.bans_file, bans)

    def is_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        bans = self._load_json(self.bans_file)
        return str(user_id) in bans

    def get_ban_reason(self, user_id: int) -> Optional[str]:
        """Get ban reason"""
        bans = self._load_json(self.bans_file)
        user_id_str = str(user_id)
        
        if user_id_str in bans:
            return bans[user_id_str].get("reason", "No reason provided")
        
        return None

    def get_all_bans(self) -> Dict[int, Dict]:
        """Get all bans"""
        bans = self._load_json(self.bans_file)
        return {int(user_id): ban for user_id, ban in bans.items()}

    # Message history
    def add_message(self, user_id: int, message_id: int, text: str, chat_id: int = None):
        """Add message to history"""
        messages = self._load_json(self.messages_file)
        user_id_str = str(user_id)
        
        if user_id_str not in messages:
            messages[user_id_str] = []
        
        messages[user_id_str].append({
            "message_id": message_id,
            "text": text,
            "chat_id": chat_id,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_json(self.messages_file, messages)

    def get_user_messages(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent messages from user"""
        messages = self._load_json(self.messages_file)
        user_id_str = str(user_id)
        
        if user_id_str not in messages:
            return []
        
        return messages[user_id_str][-limit:]

    def clear_messages(self, user_id: int):
        """Clear message history for user"""
        messages = self._load_json(self.messages_file)
        user_id_str = str(user_id)
        
        if user_id_str in messages:
            del messages[user_id_str]
            self._save_json(self.messages_file, messages)

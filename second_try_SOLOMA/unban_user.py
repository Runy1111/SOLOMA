#!/usr/bin/env python3
"""
Script to unban a user from the moderation system
"""
import sys
from storage.storage import Storage

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 unban_user.py <user_id>")
        print("Example: python3 unban_user.py 12345")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid user ID")
        sys.exit(1)
    
    storage = Storage()
    
    # Check if user is banned
    if not storage.is_banned(user_id):
        print(f"❌ User {user_id} is not banned")
        sys.exit(0)
    
    # Get ban reason
    reason = storage.get_ban_reason(user_id)
    print(f"📋 Current ban info:")
    print(f"   User ID: {user_id}")
    print(f"   Reason: {reason}")
    
    # Unban user
    storage.unban_user(user_id)
    print(f"\n✅ User {user_id} has been unbanned")
    
    # Clear violations
    storage.clear_violations(user_id)
    print(f"✅ Violations for user {user_id} have been cleared")
    
    print(f"\n✔️ User {user_id} is now fully restored")

if __name__ == "__main__":
    main()

"""
Configuration file for the Telegram moderation bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# GigaChat API
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID", "")
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY", "")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")

# Moderation settings
MAX_VIOLATIONS_FOR_BAN = int(os.getenv("MAX_VIOLATIONS_FOR_BAN", "3"))
SPAM_SIMILARITY_THRESHOLD = float(os.getenv("SPAM_SIMILARITY_THRESHOLD", "0.85"))
MESSAGE_HISTORY_SIZE = int(os.getenv("MESSAGE_HISTORY_SIZE", "10"))

# Storage
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "json")  # 'json' or 'sqlite'
STORAGE_PATH = os.getenv("STORAGE_PATH", "data/")

# Logging
LOG_FILE = os.getenv("LOG_FILE", "logs.txt")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Debug mode
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

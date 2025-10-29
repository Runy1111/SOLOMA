import os
from dotenv import load_dotenv

load_dotenv()


# LLM API
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_SYSTEM_PROMPT = os.getenv("LLM_SYSTEM_PROMPT", "You are a helpful assistant.")


BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# AntiZapret integration removed — константа была удалена

# Настройки анализа
ANALYSIS_CONFIG = {
    'fast_check_threshold': 0.3,
    'deep_analysis_threshold': 0.6,
    'critical_threshold': 0.8,
    'cache_ttl': 3600,  # 1 час
    'max_context_messages': 50
}

# Уровни риска
RISK_LEVELS = {
    'low': '🟢',
    'medium': '🟡',
    'high': '🟠', 
    'critical': '🔴'
}

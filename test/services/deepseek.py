import aiohttp
import json
import logging
from typing import Dict
from config import LLM_API_KEY, LLM_API_URL, LLM_MODEL, LLM_SYSTEM_PROMPT

class DeepSeekAnalyzer:
    """Сервис для работы с LLM API"""
    
    def __init__(self):
        self.api_key = LLM_API_KEY
        self.api_url = LLM_API_URL
        self.model = LLM_MODEL
    
    async def analyze_toxicity(self, text: str) -> Dict:
        """Анализ текста на экстремизм через LLM API"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": LLM_SYSTEM_PROMPT + """Ты - эксперт по анализу экстремистского контента. 
                            Проанализируй текст и верни JSON строго такого вида:
                            {"toxicity_score": 0.85, "risk_level": "high", "reasons": ["..."]}"""
                        },
                        {
                            "role": "user", 
                            "content": text
                        }
                    ],
                    "temperature": 0.2,
                    "max_tokens": 500
                }
                
                async with session.post(
                    self.api_url, 
                    headers=headers, 
                    json=payload
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        result_text = data['choices'][0]['message']['content']
                        return json.loads(result_text)
                    else:
                        return await self._fallback_analysis(text)
                        
        except Exception as e:
            logging.error(f"LLM API error: {e}")
            return await self._fallback_analysis(text)
    
    async def _fallback_analysis(self, text: str) -> Dict:
        """Fallback анализ при ошибках API"""
        return {
            "toxicity_score": 0.0,
            "risk_level": "low", 
            "reasons": ["Ошибка анализа API"]
        }

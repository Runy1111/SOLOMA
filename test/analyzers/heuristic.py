import re
from typing import List

class HeuristicAnalyzer:
    """Эвристический анализатор для быстрой проверки"""
    
    def __init__(self):
        self.danger_phrases = [
            r'\bубить\b', r'\bуничтожить\b', r'\bсмерть\b', r'\bненавижу\b',
            r'\bтерроризм', r'\bвзорвать\b', r'\bстрелять\b', r'\bвойна\b'
        ]
        
        self.aggressive_words = [
            'ублюдок', 'мудак', 'тварь', 'сволочь', 'сука'
        ]
    
    def analyze(self, text: str) -> float:
        """Быстрая эвристическая проверка"""
        score = 0.0
        text_lower = text.lower()
        
        # Проверка опасных фраз
        for phrase in self.danger_phrases:
            if re.search(phrase, text_lower):
                score += 0.1
        
        # Проверка агрессивных слов
        for word in self.aggressive_words:
            if word in text_lower:
                score += 0.05
        
        # Учет длины текста
        words = text.split()
        if len(words) > 20 and score > 0.2:
            score *= 1.3
        
        return min(score, 1.0)
    
    def extract_domains(self, text: str) -> List[str]:
        """Извлечение доменов из текста"""
        domain_pattern = r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+'
        domains = re.findall(domain_pattern, text)
        
        # Обходные варианты
        obfuscated = re.findall(
            r'([a-zA-Z0-9-]+\[\.\][a-zA-Z0-9-]+(?:\.[a-zA-Z]+)?)', 
            text
        )
        for domain in obfuscated:
            domains.append(domain.replace('[.]', '.'))
        
        return list(set(domains))

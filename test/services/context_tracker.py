import re
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import List, Dict, Set
from models.analysis import ContextualViolation

class ContextualMentionTracker:
    """Трекер контекстных упоминаний запрещенных ресурсов"""
    
    def __init__(self, max_history: int = 50, cleanup_hours: int = 24):
        self.banned_domains_mentioned = defaultdict(set)
        self.mention_history = defaultdict(lambda: deque(maxlen=max_history))
        self.cleanup_hours = cleanup_hours
        
        # Паттерны для контекстных упоминаний
        self.context_patterns = [
            r'(помните|помнишь|а помните|а помнишь).*?(сайт|ресурс|ссылк[ау])',
            r'(тот|тот самый).*?(сайт|ресурс)',
            r'(заблокировали|запретили).*?(сайт|ресурс)',
            r'(ранее|раньше).*?(упоминал|ссылался)',
            r'(который|которую).*?(заблокировали|удалили)'
        ]
    
    def track_mention(self, chat_id: int, domain: str, user_id: int, message: str):
        """Отслеживаем упоминание запрещенного домена"""
        self.banned_domains_mentioned[chat_id].add(domain)
        self.mention_history[chat_id].append({
            'domain': domain,
            'user_id': user_id,
            'timestamp': datetime.now(),
            'message_preview': message[:100]
        })
    
    def check_contextual_reference(self, text: str, chat_id: int) -> List[ContextualViolation]:
        """Проверяем контекстные ссылки на запрещенные ресурсы"""
        text_lower = text.lower()
        violations = []
        
        # Проверяем наличие контекстных паттернов
        has_context = any(
            re.search(pattern, text_lower) 
            for pattern in self.context_patterns
        )
        
        if not has_context:
            return violations
        
        # Проверяем упоминания известных запрещенных доменов
        for domain in self.banned_domains_mentioned.get(chat_id, set()):
            domain_name = domain.split('.')[0]
            if len(domain_name) > 3 and domain_name in text_lower:
                violations.append(
                    ContextualViolation(
                        type='contextual_mention',
                        domain=domain,
                        reason=f'Контекстное упоминание запрещенного ресурса "{domain}"',
                        risk_level='high'
                    )
                )
        
        return violations
    
    def get_recent_mentions(self, chat_id: int, hours: int = 24) -> List[Dict]:
        """Получаем недавние упоминания"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            mention for mention in self.mention_history.get(chat_id, [])
            if mention['timestamp'] > cutoff
        ]
    
    def cleanup_old_mentions(self):
        """Очистка старых упоминаний"""
        cutoff = datetime.now() - timedelta(hours=self.cleanup_hours)
        
        for chat_id in list(self.mention_history.keys()):
            self.mention_history[chat_id] = deque(
                [m for m in self.mention_history[chat_id] if m['timestamp'] > cutoff],
                maxlen=self.mention_history[chat_id].maxlen
            )

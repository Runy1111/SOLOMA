import re
from dataclasses import dataclass


@dataclass
class CorrectionResult:
    text: str


class CorrectorAgent:
    
    def init(self):
        # ВСЁ В init — никаких аннотаций, никаких r | None
        self._profanity_patterns = [
            (re.compile(r"\bх+у+[йеёя]\w*\b", re.IGNORECASE), "неуместное выражение"),
            (re.compile(r"\bп+и+з+д+\w*\b", re.IGNORECASE), "крайне неприятная ситуация"),
            (re.compile(r"\bе+б+а+н+\w*\b", re.IGNORECASE), "очень"),
            (re.compile(r"\bб+л+я+[дт]?\w*\b", re.IGNORECASE), "неприятно"),
            (re.compile(r"\bс+у+к+\w*\b", re.IGNORECASE), "досадно"),
            (re.compile(r"\b[ёе]б[ао]н\b", re.IGNORECASE), "очень"),
            (re.compile(r"\bху[йя]\b", re.IGNORECASE), "неуместное выражение"),
        ]
        
        self._masked_profanity_patterns = [
            re.compile(r"х[\*\@\#\.\-]?у[\*\@\#\.\-]?[йеёя]", re.IGNORECASE),
            re.compile(r"п[\*\@\#\.\-]?и[\*\@\#\.\-]?з[\*\@\#\.\-]?д", re.IGNORECASE),
            re.compile(r"е[\*\@\#\.\-]?б[\*\@\#\.\-]?а[\*\@\#\.\-]?н", re.IGNORECASE),
            re.compile(r"б[\*\@\#\.\-]?л[\*\@\#\.\-]?я", re.IGNORECASE),
            re.compile(r"с[\*\@\#\.\-]?у[\*\@\#\.\-]?к", re.IGNORECASE),
        ]
        
        self._direct_attack_patterns = [
            re.compile(r"\bты\b.*\bидиот\b", re.IGNORECASE),
            re.compile(r"\bты\b.*\bдебил\b", re.IGNORECASE),
            re.compile(r"\bты\b.*\bтуп[ои]й\b", re.IGNORECASE),
            re.compile(r"\bты\b.*\bне понимаешь\b", re.IGNORECASE),
            re.compile(r"\bты\b.*\bдостал\b", re.IGNORECASE),
        ]
        
        self._emotional_words = {
            "бесит": "Это вызывает раздражение",
            "жесть": "Ситуация выглядит напряжённой",
            "кошмар": "Ситуация выглядит крайне неприятной",
            "ерунда": "Это выглядит не совсем корректно",
            "чушь": "Это вызывает сомнения",
            "ненавижу": "Мне это не нравится",
            "глупо": "Это не совсем логично",
        }

    def correct(self, text):
        if not text or not text.strip():
            return CorrectionResult(text="")
        
        normalized = text.strip()
        
        # 1. Проверка мата
        profanity_result = self._check_profanity(normalized)
        if profanity_result:
            return CorrectionResult(text=self._add_punctuation(profanity_result))
        
        # 2. Прямая агрессия
        if self._is_direct_attack(normalized):
            return CorrectionResult(text="Похоже, возникло недопонимание.")
        
        # 3. Обвинительное "ты"
        if normalized.lower().startswith(("ты ", "ты,")):
            return CorrectionResult(text="Кажется, у нас разные взгляды на эту ситуацию.")
        
        # 4. Эмоциональные слова
        emotional_result = self._check_emotional_words(normalized)
        if emotional_result:
            return CorrectionResult(text=self._add_punctuation(emotional_result))
        
        # 5. Чистый текст
        return CorrectionResult(text=self._add_punctuation(normalized))

    def _check_profanity(self, text):
        original = text
        result = text
        detected = False
        
        for pattern, replacement in self._profanity_patterns:
            if pattern.search(text):
                detected = True
                result = pattern.sub(replacement, result)
        
        for pattern in self._masked_profanity_patterns:
            if pattern.search(text):
                detected = True
                result = pattern.sub("неуместное выражение", result)
        
        if not detected:
            return None
        
        if result.strip().lower() == original.strip().lower():
            return "Сообщение было переформулировано из-за резкой лексики"
        
        return result

    def _is_direct_attack(self, text):
        lowered = text.lower()
        for pattern in self._direct_attack_patterns:
            if pattern.search(lowered):
                return True
        return False
    def _check_emotional_words(self, text):
        words = re.findall(r'\b\w+\b', text.lower())
        for word in words:
            if word in self._emotional_words:
                return self._emotional_words[word]
        return None

    def _add_punctuation(self, text):
        text = text.strip()
        if not text:
            return ""
        if re.search(r'[.!?]$', text):
            return text
        return text + "."
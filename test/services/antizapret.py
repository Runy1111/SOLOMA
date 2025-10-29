"""
AntiZapret integration removed — stub implementation.

Реализация оставлена как лёгкая заглушка, чтобы другие части кода,
которые импортировали сервис, не ломались. Метод check_domain
возвращает, что домен не заблокирован.
"""

from typing import Dict


class AntiZapretService:
    """Stub: раньше выполнял запросы к внешнему API, теперь просто возвращает безопасный результат."""

    def __init__(self):
        pass

    async def check_domain(self, domain: str) -> Dict:
        """Возвращает нейтральный результат без внешних запросов."""
        return {"blocked": False, "domain": domain, "risk_level": "low"}

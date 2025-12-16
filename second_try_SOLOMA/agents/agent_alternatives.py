"""
Agent 2: Enhanced Alternatives Finder
Находит и анализирует альтернативные сервисы для заблокированных URL
"""
import re
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from datetime import datetime
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum

from gigachat_client import GigachatClient
from config.settings import GIGACHAT_CLIENT_ID, GIGACHAT_AUTH_KEY, GIGACHAT_SCOPE


class ContentType(Enum):
    """Типы контента/сервисов"""
    VIDEO_HOSTING = "видеохостинг"
    SOCIAL_NETWORK = "социальная сеть"
    MESSENGER = "мессенджер"
    CLOUD_STORAGE = "облачное хранилище"
    CODE_HOSTING = "хостинг кода"
    BLOG_PLATFORM = "блог-платформа"
    NEWS = "новостной сайт"
    FORUM = "форум"
    SEARCH_ENGINE = "поисковая система"
    EMAIL_SERVICE = "почтовый сервис"
    OTHER = "другой тип"
    ERROR = "ошибка"


@dataclass
class AlternativeService:
    """Расширенная модель альтернативного сервиса"""
    name: str
    description: str
    url: str = ""
    category: str = ""
    price_model: str = "бесплатно"  # бесплатно/фримиум/платно
    russian_support: bool = True
    region_popularity: Dict[str, str] = field(default_factory=dict)  # регион -> популярность
    accessibility_score: float = 0.0  # оценка доступности (0-1)
    legal_status: str = "легальный"
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    traffic_estimate: Optional[int] = None
    rating: float = 0.0


@dataclass
class AlternativeResult:
    """Результат поиска альтернатив"""
    content_type: str
    original_domain: str
    alternatives: List[Dict[str, str]]  # Совместимость с оригинальным форматом
    processing_time: float = 0.0
    quality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Конвертация в словарь для JSON"""
        return {
            "content_type": self.content_type,
            "original_domain": self.original_domain,
            "alternatives": self.alternatives,
            "processing_time": self.processing_time,
            "quality_score": self.quality_score,
            "alternatives_count": len(self.alternatives)
        }


class LRUCache:
    """LRU кэш для хранения результатов"""
    
    def __init__(self, maxsize: int = 1000):
        self.cache = OrderedDict()
        self.maxsize = maxsize
    
    def get(self, key: str):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, value: Any):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)
    
    def __contains__(self, key: str) -> bool:
        return key in self.cache


class EnhancedAlternativesAgent:
    """
    Улучшенный агент для поиска альтернативных сервисов
    
    Основные улучшения:
    1. Кэширование результатов
    2. Fallback база известных альтернатив
    3. Расширенный анализ доменов
    4. Аналитика качества
    5. Поддержка фильтров и предпочтений
    6. Многоязычность
    """
    
    # Известные домены и их категории
    KNOWN_DOMAINS = {
        # Видеохостинги
        'youtube.com': ContentType.VIDEO_HOSTING,
        'youtu.be': ContentType.VIDEO_HOSTING,
        'vimeo.com': ContentType.VIDEO_HOSTING,
        'dailymotion.com': ContentType.VIDEO_HOSTING,
        'rutube.ru': ContentType.VIDEO_HOSTING,
        'vk.com/video': ContentType.VIDEO_HOSTING,
        'twitch.tv': ContentType.VIDEO_HOSTING,
        
        # Социальные сети
        'vk.com': ContentType.SOCIAL_NETWORK,
        'facebook.com': ContentType.SOCIAL_NETWORK,
        'twitter.com': ContentType.SOCIAL_NETWORK,
        'x.com': ContentType.SOCIAL_NETWORK,
        'instagram.com': ContentType.SOCIAL_NETWORK,
        'linkedin.com': ContentType.SOCIAL_NETWORK,
        'ok.ru': ContentType.SOCIAL_NETWORK,
        'tiktok.com': ContentType.SOCIAL_NETWORK,
        
        # Мессенджеры
        'telegram.org': ContentType.MESSENGER,
        'telegram.me': ContentType.MESSENGER,
        'whatsapp.com': ContentType.MESSENGER,
        'viber.com': ContentType.MESSENGER,
        'signal.org': ContentType.MESSENGER,
        'discord.com': ContentType.MESSENGER,
        
        # Облачные хранилища
        'dropbox.com': ContentType.CLOUD_STORAGE,
        'drive.google.com': ContentType.CLOUD_STORAGE,
        'mega.nz': ContentType.CLOUD_STORAGE,
        'yandex.ru/disk': ContentType.CLOUD_STORAGE,
        'icloud.com': ContentType.CLOUD_STORAGE,
        'onedrive.live.com': ContentType.CLOUD_STORAGE,
        
        # Хостинг кода
        'github.com': ContentType.CODE_HOSTING,
        'gitlab.com': ContentType.CODE_HOSTING,
        'bitbucket.org': ContentType.CODE_HOSTING,
        'sourceforge.net': ContentType.CODE_HOSTING,
        
        # Блог-платформы
        'medium.com': ContentType.BLOG_PLATFORM,
        'habr.com': ContentType.BLOG_PLATFORM,
        'vc.ru': ContentType.BLOG_PLATFORM,
        'dzen.ru': ContentType.BLOG_PLATFORM,
        'zen.yandex.ru': ContentType.BLOG_PLATFORM,
        
        # Новости
        'bbc.com': ContentType.NEWS,
        'cnn.com': ContentType.NEWS,
        'nytimes.com': ContentType.NEWS,
        'lenta.ru': ContentType.NEWS,
        'ria.ru': ContentType.NEWS,
        'tass.ru': ContentType.NEWS,
        'rt.com': ContentType.NEWS,
    }
    
    # Fallback база альтернатив (совместимый формат)
    FALLBACK_ALTERNATIVES = {
        ContentType.VIDEO_HOSTING: [
            {"name": "Rutube", "description": "Российский видеохостинг с широким выбором контента"},
            {"name": "VK Видео", "description": "Видеоплатформа в социальной сети ВКонтакте"},
            {"name": "Яндекс.Эфир", "description": "Платформа для прямых трансляций от Яндекса"},
        ],
        ContentType.SOCIAL_NETWORK: [
            {"name": "ВКонтакте", "description": "Крупнейшая социальная сеть в России и СНГ"},
            {"name": "Одноклассники", "description": "Социальная сеть для общения с друзьями и знакомыми"},
        ],
        ContentType.MESSENGER: [
            {"name": "Telegram", "description": "Мессенджер с акцентом на скорость и безопасность"},
            {"name": "Viber", "description": "Мессенджер с бесплатными звонками и сообщениями"},
        ],
    }
    
    def __init__(
        self,
        use_cache: bool = True,
        cache_size: int = 1000,
        timeout: int = 30,
        language: str = 'ru',
        region: str = 'ru',
        enable_fallback: bool = True,
        log_level: str = 'INFO'
    ):
        """
        Инициализация улучшенного агента
        
        Args:
            use_cache: Включить кэширование
            cache_size: Максимальный размер кэша
            timeout: Таймаут запросов в секундах
            language: Язык ответов (ru/en)
            region: Регион для поиска альтернатив
            enable_fallback: Использовать fallback базу
            log_level: Уровень логирования
        """
        self.client = GigachatClient(
            client_id=GIGACHAT_CLIENT_ID,
            auth_key=GIGACHAT_AUTH_KEY,
            scope=GIGACHAT_SCOPE
        )
        
        self.use_cache = use_cache
        if use_cache:
            self.cache = LRUCache(maxsize=cache_size)
        
        self.timeout = timeout
        self.language = language
        self.region = region
        self.enable_fallback = enable_fallback
        
        # Настройка логирования
        self.logger = self._setup_logger(log_level)
        
        # Статистика
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'fallback_used': 0,
            'avg_processing_time': 0.0,
            'domains_searched': {}
        }
        
        self.logger.info(f"EnhancedAlternativesAgent инициализирован: language={language}, region={region}")

    def _setup_logger(self, log_level: str) -> logging.Logger:
        """Настройка логирования"""
        logger = logging.getLogger(__name__)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        logger.setLevel(getattr(logging, log_level.upper()))
        return logger

    def _extract_domain(self, url: str) -> str:
        """
        Улучшенное извлечение домена из URL
        
        Args:
            url: URL для анализа
            
        Returns:
            Извлеченный домен
        """
        try:
            # Добавляем протокол, если отсутствует
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Парсинг URL
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Удаляем www.
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Для длинных доменов оставляем последние 2-3 части
            parts = domain.split('.')
            if len(parts) > 2:
                # Исключения для специальных доменов
                special_tlds = ['co.uk', 'com.au', 'org.uk', 'ac.uk']
                for tld in special_tlds:
                    if domain.endswith(tld):
                        # Оставляем 3 части для специальных TLD
                        return '.'.join(parts[-3:])
                
                # Для обычных доменов оставляем 2 части
                return '.'.join(parts[-2:])
            
            return domain
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения домена из {url}: {e}")
            # Резервный метод
            match = re.search(r'(?:https?://)?(?:www\.)?([^/]+)', url)
            if match:
                return match.group(1).lower()
            return url

    def _detect_content_type(self, domain: str) -> ContentType:
        """
        Определение типа контента по домену
        
        Args:
            domain: Домен для анализа
            
        Returns:
            Тип контента
        """
        # Проверяем известные домены
        for known_domain, content_type in self.KNOWN_DOMAINS.items():
            if known_domain in domain:
                return content_type
        
        # Анализ по ключевым словам
        domain_lower = domain.lower()
        
        video_keywords = ['video', 'tube', 'stream', 'tv']
        social_keywords = ['social', 'network', 'connect', 'share']
        messenger_keywords = ['chat', 'message', 'telegram', 'whatsapp']
        cloud_keywords = ['cloud', 'storage', 'drive', 'disk']
        
        for keyword in video_keywords:
            if keyword in domain_lower:
                return ContentType.VIDEO_HOSTING
        
        for keyword in social_keywords:
            if keyword in domain_lower:
                return ContentType.SOCIAL_NETWORK
        
        for keyword in messenger_keywords:
            if keyword in domain_lower:
                return ContentType.MESSENGER
        
        for keyword in cloud_keywords:
            if keyword in domain_lower:
                return ContentType.CLOUD_STORAGE
        
        return ContentType.OTHER

    def _get_system_prompt(self) -> str:
        """
        Получение системного промпта в зависимости от языка
        
        Returns:
            Системный промпт
        """
        if self.language == 'en':
            return """You are an assistant for finding alternative services.

Requirements:
1. Determine the SERVICE TYPE from the URL (video hosting, social network, messenger, cloud storage, etc.)
2. Suggest 3-5 popular, legal, and relevant alternatives
3. For each alternative, provide only:
   - Name
   - Brief description
4. Focus on services available in the specified region

Format your response:
TYPE: [service type]
ALTERNATIVES:
1. [Name] - [Description]
2. [Name] - [Description]
..."""
        
        # Русский промпт по умолчанию
        return """Ты помощник для поиска альтернативных сервисов.

Требования:
1. Определи ТИП СЕРВИСА по URL (видеохостинг, соц. сеть, мессенджер, облачное хранилище и т.д.)
2. Предложи 3-5 популярных, легальных и релевантных альтернатив
3. Для каждой альтернативы укажи только:
   - Название
   - Краткое описание
4. Фокусируйся на сервисах, доступных в указанном регионе

Формат ответа:
ТИП: [тип сервиса]
АЛЬТЕРНАТИВЫ:
1. [Название] - [Описание]
2. [Название] - [Описание]
..."""

    def _parse_response(self, response: str, domain: str) -> AlternativeResult:
        """
        Парсинг ответа от ИИ в совместимом формате
        
        Args:
            response: Ответ от языковой модели
            domain: Исходный домен
            
        Returns:
            Структурированный результат
        """
        try:
            # Извлечение типа сервиса
            content_type = "неизвестный тип"
            type_match = re.search(r"ТИП:\s*(.+?)(?=\n|$)", response, re.IGNORECASE)
            if not type_match:
                type_match = re.search(r"TYPE:\s*(.+?)(?=\n|$)", response, re.IGNORECASE)
            
            if type_match:
                content_type = type_match.group(1).strip()
            
            # Извлечение альтернатив (совместимый формат)
            alternatives = []
            
            # Ищем раздел с альтернативами
            alt_section_match = re.search(
                r"АЛЬТЕРНАТИВЫ:(.+?)(?=$|\n\s*\n)",
                response,
                re.IGNORECASE | re.DOTALL
            )
            
            if not alt_section_match:
                alt_section_match = re.search(
                    r"ALTERNATIVES:(.+?)(?=$|\n\s*\n)",
                    response,
                    re.IGNORECASE | re.DOTALL
                )
            
            if alt_section_match:
                alt_text = alt_section_match.group(1)
                
                # Парсинг по старому формату: "1. Название - Описание"
                lines = alt_text.strip().split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Убираем номер и точку
                    line = re.sub(r'^\d+\.\s*', '', line)
                    
                    # Разделяем по дефису
                    if ' - ' in line:
                        name, description = line.split(' - ', 1)
                        alternatives.append({
                            "name": name.strip(),
                            "description": description.strip()
                        })
                    elif ': ' in line:
                        name, description = line.split(': ', 1)
                        alternatives.append({
                            "name": name.strip(),
                            "description": description.strip()
                        })
            
            # Если не удалось распарсить, используем простой парсинг
            if not alternatives:
                self.logger.warning("Не удалось распарсить ответ, использую простой парсинг")
                alt_pattern = r'(\d+)\.\s*(.+?)\s*-\s*(.+?)(?=\n\d+\.|$)'
                alt_matches = re.findall(alt_pattern, response, re.DOTALL)
                
                for num, name, desc in alt_matches:
                    alternatives.append({
                        "name": name.strip(),
                        "description": desc.strip()
                    })
            
            # Оценка качества результата
            quality_score = self._calculate_quality_score(content_type, alternatives)
            
            return AlternativeResult(
                content_type=content_type,
                original_domain=domain,
                alternatives=alternatives,
                quality_score=quality_score
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга ответа: {e}")
            return AlternativeResult(
                content_type="ошибка парсинга",
                original_domain=domain,
                alternatives=[{"name": "Ошибка", "description": f"Не удалось обработать ответ: {str(e)}"}],
                quality_score=0.0
            )

    def _calculate_quality_score(self, content_type: str, alternatives: List[Dict]) -> float:
        """
        Оценка качества результата
        
        Args:
            content_type: Тип контента
            alternatives: Список альтернатив
            
        Returns:
            Оценка качества от 0 до 1
        """
        score = 0.0
        
        # Оценка за тип контента
        if content_type != "неизвестный тип" and content_type != "ошибка":
            score += 0.3
        
        # Оценка за количество альтернатив
        if len(alternatives) >= 3:
            score += 0.3
        if len(alternatives) >= 5:
            score += 0.2
        
        # Оценка за полноту информации
        for alt in alternatives:
            if alt.get('description') and len(alt['description']) > 10:
                score += 0.05
        
        # Ограничиваем максимум 1.0
        return min(score, 1.0)

    async def _get_fallback_alternatives(self, domain: str, content_type: ContentType) -> AlternativeResult:
        """
        Получение альтернатив из fallback базы
        
        Args:
            domain: Исходный домен
            content_type: Тип контента
            
        Returns:
            Результат из fallback базы
        """
        self.stats['fallback_used'] += 1
        self.logger.info(f"Использую fallback альтернативы для {domain}")
        
        if content_type in self.FALLBACK_ALTERNATIVES:
            alternatives = self.FALLBACK_ALTERNATIVES[content_type]
        else:
            # Общие альтернативы для неизвестных типов
            alternatives = [
                {"name": "Поиск аналогов", "description": f"Используйте поиск по запросу '{content_type.value if isinstance(content_type, ContentType) else content_type}'"}
            ]
        
        return AlternativeResult(
            content_type=content_type.value if isinstance(content_type, ContentType) else str(content_type),
            original_domain=domain,
            alternatives=alternatives,
            quality_score=0.5  # Средняя оценка для fallback
        )

    async def find_alternatives(
        self,
        url: str,
        user_preferences: Dict[str, Any] = None,
        filters: Dict[str, Any] = None
    ) -> AlternativeResult:
        """
        Основной метод поиска альтернатив (совместим с оригиналом)
        
        Args:
            url: URL для поиска альтернатив
            user_preferences: Предпочтения пользователя (не используется для совместимости)
            filters: Фильтры для результатов (не используется для совместимости)
            
        Returns:
            Результат поиска альтернатив в совместимом формате
        """
        start_time = time.time()
        self.stats['total_requests'] += 1
        
        try:
            # Извлечение домена
            domain = self._extract_domain(url)
            self.stats['domains_searched'][domain] = self.stats['domains_searched'].get(domain, 0) + 1
            
            # Проверка кэша
            cache_key = f"{domain}_{self.language}_{self.region}"
            if self.use_cache and self.cache and cache_key in self.cache:
                self.stats['cache_hits'] += 1
                self.logger.info(f"Кэш-попадание для {domain}")
                result = self.cache.get(cache_key)
                result.processing_time = time.time() - start_time
                return result
            
            # Определение типа контента
            content_type = self._detect_content_type(domain)
            self.logger.info(f"Анализирую {domain}, тип: {content_type}")
            
            # Формирование запроса к ИИ
            system_prompt = self._get_system_prompt()
            
            # Добавление региона в промпт
            if self.language == 'ru':
                system_prompt += f"\n\nРегион пользователя: {self.region}"
            else:
                system_prompt += f"\n\nUser region: {self.region}"
            
            user_message = f"Домен: {domain}\nПолный URL: {url}"
            
            # Асинхронный запрос с таймаутом
            try:
                response = await asyncio.wait_for(
                    self.client.generate(user_message, system_prompt=system_prompt),
                    timeout=self.timeout
                )
                
                # Парсинг ответа
                result = self._parse_response(response, domain)
                result.processing_time = time.time() - start_time
                
                # Сохранение в кэш
                if self.use_cache and self.cache:
                    self.cache.put(cache_key, result)
                
                self.stats['successful_requests'] += 1
                self.stats['avg_processing_time'] = (
                    (self.stats['avg_processing_time'] * (self.stats['successful_requests'] - 1) + result.processing_time)
                    / self.stats['successful_requests']
                )
                
                self.logger.info(f"Успешно найдено {len(result.alternatives)} альтернатив для {domain}")
                return result
                
            except asyncio.TimeoutError:
                self.logger.warning(f"Таймаут при поиске альтернатив для {domain}")
                result = await self._get_fallback_alternatives(domain, content_type)
                result.processing_time = time.time() - start_time
                return result
                
            except Exception as e:
                self.logger.error(f"Ошибка при запросе к ИИ для {domain}: {e}")
                result = await self._get_fallback_alternatives(domain, content_type)
                result.processing_time = time.time() - start_time
                return result
                
        except Exception as e:
            self.stats['failed_requests'] += 1
            self.logger.error(f"Критическая ошибка при обработке {url}: {e}")
            
            return AlternativeResult(
                content_type=ContentType.ERROR.value,
                original_domain=url,
                alternatives=[{"name": "Системная ошибка", "description": f"Произошла ошибка при обработке запроса: {str(e)}"}],
                processing_time=time.time() - start_time,
                quality_score=0.0
            )

    async def batch_find_alternatives(
        self,
        urls: List[str],
        max_concurrent: int = 5
    ) -> Dict[str, AlternativeResult]:
        """
        Пакетный поиск альтернатив
        
        Args:
            urls: Список URL для анализа
            max_concurrent: Максимальное количество параллельных запросов
            
        Returns:
            Словарь с результатами для каждого URL
        """
        self.logger.info(f"Начинаю пакетную обработку {len(urls)} URL")
        
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_url(url: str):
            async with semaphore:
                try:
                    result = await self.find_alternatives(url)
                    return url, result
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке {url}: {e}")
                    return url, AlternativeResult(
                        content_type=ContentType.ERROR.value,
                        original_domain=url,
                        alternatives=[{"name": "Ошибка обработки", "description": f"Не удалось обработать URL: {str(e)}"}],
                        quality_score=0.0
                    )
        
        # Создаем задачи для всех URL
        tasks = [process_url(url) for url in urls]
        
        # Запускаем все задачи параллельно
        batch_results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Формируем словарь результатов
        for url, result in batch_results:
            results[url] = result
        
        self.logger.info(f"Пакетная обработка завершена: {len(results)} результатов")
        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики работы агента
        
        Returns:
            Статистика
        """
        cache_hit_rate = 0
        if self.stats['total_requests'] > 0:
            cache_hit_rate = self.stats.get('cache_hits', 0) / self.stats['total_requests']
        
        success_rate = 0
        if self.stats['total_requests'] > 0:
            success_rate = self.stats['successful_requests'] / self.stats['total_requests']
        
        return {
            **self.stats,
            'cache_hit_rate': cache_hit_rate,
            'success_rate': success_rate,
            'timestamp': datetime.now().isoformat(),
            'language': self.language,
            'region': self.region,
            'cache_enabled': self.use_cache,
            'cache_size': len(self.cache.cache) if self.use_cache and self.cache else 0
        }

    def clear_cache(self):
        """Очистка кэша"""
        if self.use_cache and self.cache:
            self.cache.cache.clear()
            self.logger.info("Кэш очищен")

    def export_results(self, result: AlternativeResult, format: str = 'json') -> Any:
        """
        Экспорт результатов в различных форматах
        
        Args:
            result: Результат для экспорта
            format: Формат экспорта (json/text/markdown)
            
        Returns:
            Данные в указанном формате
        """
        if format == 'json':
            return result.to_dict()
        
        elif format == 'text':
            text = f"Альтернативы для: {result.original_domain}\n"
            text += f"Тип сервиса: {result.content_type}\n"
            text += f"Найдено альтернатив: {len(result.alternatives)}\n"
            text += f"Время обработки: {result.processing_time:.2f}с\n"
            text += f"Оценка качества: {result.quality_score:.2f}\n\n"
            
            for i, alt in enumerate(result.alternatives, 1):
                text += f"{i}. {alt['name']}\n"
                text += f"   Описание: {alt['description']}\n"
                text += "\n"
            
            return text
        
        elif format == 'markdown':
            md = f"# Альтернативы для: {result.original_domain}\n\n"
            md += f"**Тип сервиса:** {result.content_type}\n\n"
            md += f"**Найдено альтернатив:** {len(result.alternatives)}\n"
            md += f"**Время обработки:** {result.processing_time:.2f}с\n"
            md += f"**Оценка качества:** {result.quality_score:.2f}\n\n"
            
            for i, alt in enumerate(result.alternatives, 1):
                md += f"## {i}. {alt['name']}\n\n"
                md += f"**Описание:** {alt['description']}\n\n"
            
            return md
        
        else:
            raise ValueError(f"Неизвестный формат: {format}")

    async def close(self):
        """Закрытие соединений"""
        await self.client.close()
        self.logger.info("EnhancedAlternativesAgent закрыт")


# Класс для обратной совместимости с оригинальным кодом
class AlternativesAgent(EnhancedAlternativesAgent):
    """
    Класс для обратной совместимости с оригинальным кодом.
    Использует EnhancedAlternativesAgent внутри, но сохраняет оригинальное имя класса.
    """
    def __init__(self):
        # Инициализируем с настройками по умолчанию для совместимости
        super().__init__(
            use_cache=True,
            cache_size=1000,
            timeout=30,
            language='ru',
            region='ru',
            enable_fallback=True,
            log_level='INFO'
        )
    
    async def find_alternatives(self, url: str) -> AlternativeResult:
        """
        Основной метод поиска альтернатив (совместимый интерфейс)
        
        Args:
            url: URL для поиска альтернатив
            
        Returns:
            Результат поиска альтернатив в совместимом формате
        """
        # Просто вызываем улучшенный метод с параметрами по умолчанию
        return await super().find_alternatives(url)


# Пример использования
async def example_usage():
    """Пример использования улучшенного агента"""
    
    # Инициализация агента (для совместимости с main.py)
    agent = AlternativesAgent()
    
    try:
        # Поиск альтернатив для одного URL
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = await agent.find_alternatives(url)
        
        print(f"Тип контента: {result.content_type}")
        print(f"Найдено альтернатив: {len(result.alternatives)}")
        print(f"Время обработки: {result.processing_time:.2f}с")
        print(f"Оценка качества: {result.quality_score:.2f}")
        
        # Вывод альтернатив
        for i, alt in enumerate(result.alternatives, 1):
            print(f"{i}. {alt['name']} - {alt['description']}")
        
        # Статистика
        stats = agent.get_stats()
        print(f"\nСтатистика: {stats}")
        
    finally:
        # Закрытие соединений
        await agent.close()


if __name__ == "__main__":
    # Запуск примера
    asyncio.run(example_usage())
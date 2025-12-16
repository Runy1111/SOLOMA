"""
Agent 1: Moderator-Coordinator
Analyzes messages for violations and classifies them
"""
import asyncio
import re
import difflib
from typing import Tuple, Optional, List
from gigachat_client import GigachatClient
from config.settings import GIGACHAT_CLIENT_ID, GIGACHAT_AUTH_KEY, GIGACHAT_SCOPE


class AnalysisResult:
    def __init__(
        self,
        category: str,  # "CLEAN", "CATEGORY_B", "CATEGORY_A", "CATEGORY_C"
        reason: str,
        has_links: bool = False,
        links: List[str] = None
    ):
        self.category = category
        self.reason = reason
        self.has_links = has_links
        self.links = links or []



class ModeratorAgent:
    def __init__(self):
        self.client = GigachatClient(
            client_id=GIGACHAT_CLIENT_ID,
            auth_key=GIGACHAT_AUTH_KEY,
            scope=GIGACHAT_SCOPE
        )
        # Загружаем список иноагентов
        # self.inoagents — множество нормализованных ФИО, self.pseudonyms — словарь псевдоним->ФИО
        self.inoagents = set()
        self.pseudonyms = {}
        self._load_inoagents()

    def _normalize(self, s):
        return s.lower().replace('ё', 'е').replace('  ', ' ').strip()

    def _ru_to_lat(self, s: str) -> str:
        """Very small transliteration map Cyrillic->Latin for fuzzy comparison."""
        table = {
            'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z','и':'i','й':'i',
            'к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f',
            'х':'h','ц':'c','ч':'ch','ш':'sh','щ':'sh','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'
        }
        s = s.lower()
        out = []
        for ch in s:
            if ch in table:
                out.append(table[ch])
            elif re.match(r'[a-z0-9]', ch):
                out.append(ch)
            # ignore other chars
        return ''.join(out)

    def _lat_to_ru_approx(self, s: str) -> str:
        """Approximate transliteration Latin->Cyrillic for stylized pseudonyms (heuristic).
        Not perfect, but helps map variants like 'Oxxxymiron' -> 'оксимирон'."""
        s = s.lower()
        table = {
            'a':'а','b':'б','c':'ц','d':'д','e':'е','f':'ф','g':'г','h':'х','i':'и','j':'й','k':'к',
            'l':'л','m':'м','n':'н','o':'о','p':'п','q':'к','r':'р','s':'с','t':'т','u':'у','v':'в',
            'w':'в','x':'кс','y':'и','z':'з','0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9'
        }
        out = []
        for ch in s:
            out.append(table.get(ch, ''))
        res = ''.join(out)
        # collapse repeated 'кс' sequences to single 'кс'
        res = re.sub(r'(кс){2,}', 'кс', res)
        # collapse repeated letters
        res = re.sub(r'(.)\1{2,}', r'\1', res)
        return res

    def _load_inoagents(self):
        import re
        inoagents_path = __file__.replace('agent_moderator.py', 'inoagents')
        fio_pattern = re.compile(r'([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)')
        # псевдонимы: ищем фразы с ключевым словом 'псевдоним' или 'под псевдонимом' и т.п.
        pseudonym_pattern = re.compile(r'псевдоним(?:[а|ом])?\s*(?:[«\"“]?)([^»\"”\n]+)(?:[»\"”])?', re.IGNORECASE)
        # стоп‑слова/общие слова, которые не являются псевдонимами
        pseudo_blacklist = {
            'проект','ресурс','команда','издание','газета','телеграм','канал','организация',
            'платформа','фонд','агент','мат','медиа','радио','сайт','новости','открытых','важных',
            'иноагент'
        }
        try:
            with open(inoagents_path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('№') or line.startswith('Список') or line.startswith('Материал'):
                        continue
                    # Ищем все ФИО в строке
                    fio_matches = fio_pattern.findall(line)
                    for match in fio_matches:
                        norm = self._normalize(match)
                        self.inoagents.add(norm)

                    # Ищем псевдонимы/алиасы в той же строке и сопоставляем их с первым найденным ФИО
                    pseudo = None
                    pm = pseudonym_pattern.search(line)
                    if pm:
                        pseudo = pm.group(1).strip()
                    # Иногда псевдоним указан в кавычках без слова 'псевдоним' — попытаемся найти краткие в кавычках
                    if not pseudo:
                        q = re.search(r'[«\"“]([^»\"”]+)[»\"”]', line)
                        if q:
                            maybe = q.group(1).strip()
                            # если в кавычках короткая строка (одно-две слова), считаем это псевдонимом
                            if len(maybe.split()) <= 3:
                                pseudo = maybe

                    if pseudo and fio_matches:
                        # сопоставим псевдоним с первым ФИО на строке
                        first_fio = self._normalize(fio_matches[0])
                        # псевдоним может быть несколько слов — добавим нормализованные варианты
                        p_norm = self._normalize(pseudo)
                        # фильтруем слишком общие или короткие псевдонимы (чтобы не брать слова вроде 'агент', 'мат')
                        if len(p_norm) < 3 or p_norm in pseudo_blacklist:
                            # пропускаем подозрительные/общие псевдонимы
                            continue
                        # сохраняем псевдоним -> ФИО
                        self.pseudonyms[p_norm] = first_fio
                        # если псевдоним содержит латинские символы, попробуем сгенерировать приближённую кириллическую форму
                        if re.search(r'[a-zA-Z]', p_norm):
                            alt = self._lat_to_ru_approx(p_norm)
                            if alt:
                                self.pseudonyms[alt] = first_fio
        except Exception as e:
            print(f"Не удалось загрузить список иноагентов: {e}")
        return self.inoagents

    async def extract_urls(self, text: str) -> List[str]:
        """Extract all URLs from text"""
        url_pattern = r'https?://[^\s]+'
        return re.findall(url_pattern, text)

    async def analyze_message(self, message: str, chat_history: Optional[List[str]] = None) -> AnalysisResult:
        """
        Analyze message for violations using GigaChat
        Returns AnalysisResult with category and reason
        """
        try:
            # Extract links
            links = await self.extract_urls(message)

            # Нормализованный текст сообщения (локальная эвристика)
            msg_norm = self._normalize(message)

            # Ранний предохранитель: если сообщение состоит из одного короткого токена из token_blacklist,
            # немедленно вернём CLEAN (или CATEGORY_B для 'мат') и не будем вызывать LLM.
            token_blacklist = {'агент','мат','чел','тут','здесь','кто','что','новости','иноагент'}
            simple_tokens = re.findall(r"[А-Яа-яёЁA-Za-z0-9\-]+", message)
            if len(simple_tokens) == 1:
                t0 = self._normalize(simple_tokens[0])
                if t0 in token_blacklist or len(t0) < 3:
                    if t0 == 'мат':
                        return AnalysisResult(category="CATEGORY_B", reason='ненормативная лексика "для выразительности"', has_links=len(links) > 0, links=links)
                    # Short common token — skip heavy processing
                    return AnalysisResult(category="CLEAN", reason="Сообщение соответствует правилам", has_links=len(links) > 0, links=links)

            # Быстрая локальная проверка: если в тексте явно содержится ФИО из реестра — возвращаем CATEGORY_C
            # Улучшение: вместо простого substring match требуем подтверждение по токенам
            # (как минимум совпадение двух токенов из ФИО — фамилия+имя) и соответствие границ слов,
            # чтобы избежать ложных срабатываний, когда ФИО встречается как часть другого слова.
            msg_tokens_all = re.findall(r"[А-Яа-яёЁA-Za-z0-9\-]+", message.lower())
            msg_tokens_set = set([self._normalize(t) for t in msg_tokens_all])
            def name_tokens(s: str):
                return [t for t in s.split() if t]

            for name in self.inoagents:
                if not name:
                    continue
                n_tokens = name_tokens(name)
                # require at least two tokens (фамилия+имя) to consider a match
                if len(n_tokens) < 2:
                    continue
                matched_tokens = 0
                for nt in n_tokens:
                    if nt in msg_tokens_set:
                        matched_tokens += 1
                if matched_tokens >= 2:
                    # additionally ensure tokens appear as separate words (word boundary check)
                    pattern = r"\b" + re.escape(n_tokens[0]) + r"\b.*\b" + re.escape(n_tokens[1]) + r"\b"
                    if re.search(pattern, msg_norm):
                        return AnalysisResult(
                            category="CATEGORY_C",
                            reason=f"Упоминание лица из реестра иноагентов: {name}",
                            has_links=len(links) > 0,
                            links=links
                        )

            # Проверка псевдонимов (одиночных слов) из реестра
            # Сначала соберём токены из сообщения
            msg_tokens = re.findall(r'[А-Яа-яёЁA-Za-z0-9\-]+', message)
            # токены-стоплист, короткие/общие слова, которые не должны считаться псевдонимами
            token_blacklist = {'агент','мат','чел','тут','здесь','кто','что','новости','иноагент'}
            for t in msg_tokens:
                t_norm = self._normalize(t)
                if len(t_norm) < 3 or t_norm in token_blacklist:
                    continue
                # точное совпадение с псевдонимом
                if t_norm in self.pseudonyms:
                    fio = self.pseudonyms[t_norm]
                    return AnalysisResult(category="CATEGORY_C", reason=f"Упоминание лица из реестра иноагентов: {fio}", has_links=len(links) > 0, links=links)
                # попытка нестрогого совпадения через транслит+fuzzy (для латинских форм типа Oxxxymiron vs оксимирон)
                # skip very short tokens to avoid accidental fuzzy matches (e.g. 'тебе' -> 'tebe')
                if len(t_norm) < 4:
                    continue
                t_lat = self._ru_to_lat(t_norm)
                for p, fio in self.pseudonyms.items():
                    # p может содержать латин символы; приведём его к ascii-only form
                    p_ascii = re.sub(r'[^a-z0-9]', '', p)
                    if not p_ascii or len(p_ascii) < 4:
                        continue
                    # require both sides to be reasonably long before fuzzy-checking
                    if len(t_lat) < 4:
                        continue
                    ratio = difflib.SequenceMatcher(None, t_lat, p_ascii).ratio()
                    # raise threshold to reduce false positives
                    if ratio >= 0.80:
                        return AnalysisResult(category="CATEGORY_C", reason=f"Упоминание лица из реестра иноагентов: {fio}", has_links=len(links) > 0, links=links)
            # Если локальные проверки не сработали, попробуем сделать таргетированный LLM-запрос для одиночных токенов
            # (например, пользователи пишут 'оксимирон' кириллицей, а в реестре псевдоним хранится латиницей 'Oxxxymiron').
            # Ограничимся короткими безопасными вызовами — по одному LLM-запросу на длинный токен.
            try:
                # skip small/common tokens from per-token LLM queries
                small_token_blacklist = {'агент','мат','чел','тут','здесь','кто','что','новости','иноагент'}
                for t in msg_tokens:
                    t_norm = self._normalize(t)
                    if len(t_norm) < 3 or t_norm in small_token_blacklist:
                        continue
                    # подготовим аккуратный prompt — просим вернуть только ФИО или пустую строку
                    alias_system_small = (
                        "Ты — инструмент, который по псевдониму определяет полное ФИО личности."
                        " Верни только ФИО (Фамилия Имя Отчество) или пустую строку, если не знаешь. Никаких пояснений."
                    )
                    alias_user_small = f"Псевдоним: '{t_norm}'. Какому ФИО он соответствует?"
                    alias_resp_small = await self.client.generate(alias_user_small, system_prompt=alias_system_small)
                    if not alias_resp_small:
                        continue
                    # парсим ответ на ФИО
                    fio_m = re.search(r'([А-ЯЁа-яё]+\s+[А-ЯЁа-яё]+(?:\s+[А-ЯЁа-яё]+)?)', alias_resp_small, re.IGNORECASE)
                    if fio_m:
                        found = self._normalize(fio_m.group(1))
                        # сравним с реестром по токенам (имя+фамилия)
                        f_tokens = set(tokens(found))
                        for reg in self.inoagents:
                            reg_tokens = set(tokens(reg))
                            if len(f_tokens & reg_tokens) >= 2:
                                return AnalysisResult(category="CATEGORY_C", reason=f"Упоминание лица из реестра иноагентов: {reg}", has_links=len(links) > 0, links=links)
            except Exception:
                # если LLM недоступен — просто продолжаем
                pass

            # Дополнительная локальная эвристика: ищем пары слов в сообщении, похожие на 'Имя Фамилия' или 'Фамилия Имя'
            # и сравниваем токенами с реестром (если совпадение по двум токенам — считаем совпадением).
            name_pair_pattern = re.compile(r'([А-Яа-яёЁ]+\s+[А-Яа-яёЁ]+)', re.IGNORECASE)
            local_candidates = set()
            # words that should not be considered as name parts
            pronouns = {'ты','вы','он','она','они','кто','что','это','здесь','там'}
            token_blacklist = {'агент','мат','чел','тут','здесь','кто','что','новости','иноагент'}
            for m in name_pair_pattern.findall(message):
                norm_m = self._normalize(m)
                parts = norm_m.split()
                # skip pairs that contain pronouns or blacklist tokens
                if any(p in pronouns or p in token_blacklist for p in parts):
                    continue
                local_candidates.add(norm_m)

            def tokens(s: str):
                return [t for t in s.split() if t]

            for cand in local_candidates:
                cand_tokens = set(tokens(cand))
                for reg in self.inoagents:
                    reg_tokens = set(tokens(reg))
                    if len(cand_tokens & reg_tokens) >= 2:
                        # Contextual filter: if candidate appears in a phrase that likely
                        # describes frequency/occurrence (e.g. "встречается часто"),
                        # skip automatic classification to reduce false positives.
                        context_block = ['встреча', 'встречается', 'часто', 'упоминается']
                        if any(ctx in msg_norm for ctx in context_block):
                            # skip this candidate and continue scanning
                            continue

                        return AnalysisResult(
                            category="CATEGORY_C",
                            reason=f"Упоминание лица из реестра иноагентов: {reg}",
                            has_links=len(links) > 0,
                            links=links
                        )

            # 1) Попытка получить от модели список ФИО, соответствующих упоминаниям/псевдонимам в сообщении.
            #    Мы НЕ передаём список иноагентов в модель (чтобы сэкономить токены). Модель должна
            #    вернуть строку ФИО, разделённых запятыми, или пустую строку.
            try:
                alias_system = (
                    "Ты — инструмент, который извлекает из текста все упоминания людей (псевдонимы, ники,"
                    " сценические имена, прозвища) и преобразует их в полные ФИО (Фамилия Имя Отчество)."
                    " Верни только одну строку — список ФИО, разделённых запятой. Никаких объяснений,"
                    " дополнительных символов или формата — только ФИО через запятую. Если никаких"
                    " людей не найдено, верни пустую строку."
                )

                alias_user = f"Найди все упоминания людей в этом тексте и верни их полные ФИО (через запятую): '{message}'"
                alias_resp = await self.client.generate(alias_user, system_prompt=alias_system)
            except Exception as e:
                # Если модель недоступна — продолжаем без неё
                alias_resp = ""

            # Разбираем строку с ФИО, возвращённую моделью
            # Делать поиск нечувствительным к регистру и разным порядкам слов (ФИО/Имя Фамилия)
            fio_pattern = re.compile(r'([А-ЯЁа-яё]+\s+[А-ЯЁа-яё]+(?:\s+[А-ЯЁа-яё]+)?)', re.IGNORECASE)
            found_fios = set()
            if alias_resp:
                # Ожидаем, что модель вернёт что-то вроде: "Иванов Иван Иванович, Петров Петр Петрович"
                cleaned = alias_resp.replace('\n', ',').strip()
                parts = [p.strip() for p in re.split(r'[;,]+', cleaned) if p.strip()]
                for p in parts:
                    # Удалим кавычки и лишние символы
                    p_clean = re.sub(r"[^А-Яа-яёЁ\s-]", '', p)
                    m = fio_pattern.search(p_clean)
                    if m:
                        found_fios.add(self._normalize(m.group(1)))

            # Функция для токенизации ФИО
            def tokens(s: str):
                return [t for t in s.split() if t]

            # Сверяем найденные ФИО с локальным реестром иноагентов.
            # Сопоставление гибкое: если пересечение токенов >= 2 (имя+фамилия) — считаем совпадением.
            matched = []
            for f in found_fios:
                f_tokens = set(tokens(f))
                for reg in self.inoagents:
                    reg_tokens = set(tokens(reg))
                    if len(f_tokens & reg_tokens) >= 2:
                        matched.append(reg)
                        break

            if matched:
                reason = f"Упоминание лица из реестра иноагентов: {', '.join(matched)}"
                return AnalysisResult(
                    category="CATEGORY_C",
                    reason=reason,
                    has_links=len(links) > 0,
                    links=links
                )

            # ...existing code...
            history_context = ""
            if chat_history:
                history_context = "\nПредыдущие сообщения в чате:\n" + "\n".join(chat_history[-3:])

            # System prompt for analysis
            # Системный prompt для классификации — без вставки большого списка иноагентов.
            system_prompt = f"""
Ты — модератор чата. Твоя задача — строго классифицировать сообщения по категориям нарушений.
Не давай нравственных оценок, не рассуждай, не добавляй лишних пояснений.

Категория B (лёгкие нарушения):
- Ненормативная лексика "для выразительности"
- Грубость, но не оскорбление
- Сарказм на грани нарушения

Категория A (серьёзные нарушения):
- Прямые личные оскорбления
- Разжигание ненависти
- Дискриминация
- Экстремистские призывы
- Угрозы

Категория C (информация о иноагентах):
- Любое упоминание конкретных лиц, признанных иноагентами, даже если не указано слово 'иноагент'.

Если сообщение не подходит ни под одну из категорий — ответь "CLEAN".

Верни ответ строго в формате (категорию выбирай из 4 вариантов — CLEAN, CATEGORY_A, CATEGORY_B, CATEGORY_C):
КАТЕГОРИЯ: [CLEAN/CATEGORY_A/CATEGORY_B/CATEGORY_C]
ПРИЧИНА: [краткое объяснение]
"""

            user_message = f"Проанализируй это сообщение:{history_context}\n\nСообщение для анализа:\n'{message}'"

            # Предохранитель: если сообщение очень короткое (один токен) и этот токен в blacklist,
            # не вызываем LLM для классификации, чтобы избежать ложных срабатываний CATEGORY_C.
            simple_tokens = re.findall(r"[А-Яа-яёЁA-Za-z0-9\-]+", message)
            if len(simple_tokens) == 1:
                t0 = self._normalize(simple_tokens[0])
                # используем тот же token_blacklist, который применяем для псевдонимов
                token_blacklist = {'агент','мат','чел','тут','здесь','кто','что','новости'}
                if t0 in token_blacklist or len(t0) < 3:
                    # краткая локальная эвристика: классифицируем как CLEAN или как спам/мат
                    # если есть ненорматив (мат), проверяем словарь ругательств
                    if t0 == 'мат':
                        return AnalysisResult(category="CATEGORY_B", reason='ненормативная лексика "для выразительности"', has_links=len(links) > 0, links=links)
                    return AnalysisResult(category="CLEAN", reason="Сообщение соответствует правилам", has_links=len(links) > 0, links=links)

            # Попытка вызвать LLM для классификации; если не удалось — делаем простую локальную эвристику
            try:
                response = await self.client.generate(user_message, system_prompt=system_prompt)

                # Parse response
                category = "CLEAN"
                reason = "Сообщение соответствует правилам"

                if "CATEGORY_A" in response or "ограничены" in response or "разговоры" in response:
                    category = "CATEGORY_A"
                    reason_match = re.search(r"ПРИЧИНА:\s*(.+?)(?=\n|$)", response, re.IGNORECASE)
                    if reason_match:
                        reason = reason_match.group(1).strip()
                elif "CATEGORY_B" in response:
                    category = "CATEGORY_B"
                    reason_match = re.search(r"ПРИЧИНА:\s*(.+?)(?=\n|$)", response, re.IGNORECASE)
                    if reason_match:
                        reason = reason_match.group(1).strip()
                elif "CATEGORY_C" in response:
                    category = "CATEGORY_C"
                    reason_match = re.search(r"ПРИЧИНА:\s*(.+?)(?=\n|$)", response, re.IGNORECASE)
                    if reason_match:
                        reason = reason_match.group(1).strip()
                # If LLM returned CATEGORY_C but we have no local evidence (no matched FIO, no name-like
                # candidate and no pseudonym present in the message), downgrade to CLEAN to avoid
                # classifying generic phrases like "ты иноагент" as mentioning a specific person.
                if category == "CATEGORY_C":
                    has_local_name = False
                    try:
                        # local_candidates was extracted earlier (pairs like 'Имя Фамилия')
                        if local_candidates:
                            has_local_name = True
                    except NameError:
                        has_local_name = False

                    # check if any token in the message matches a known pseudonym
                    msg_tokens_check = re.findall(r"[А-Яа-яёЁA-Za-z0-9\-]+", message)
                    for t in msg_tokens_check:
                        if self._normalize(t) in self.pseudonyms:
                            has_local_name = True
                            break

                    if not matched and not has_local_name:
                        # downgrade
                        category = "CLEAN"
                        reason = "Сообщение соответствует правилам"
                print(f"Moderation result: {category}, {reason}")
                return AnalysisResult(
                    category=category,
                    reason=reason,
                    has_links=len(links) > 0,
                    links=links
                )
            except Exception:
                # Локальная эвристическая классификация (работает оффлайн)
                low_text = msg_norm
                # Простые маркеры угроз/экстремизма
                threat_words = ["убью", "порв", "убь", "поджог", "взорв", "уничтож", "расстрел"]
                rude_words = ["дурак", "тупой", "идиот", "сволочь", "мерзавец", "ублюдок"]

                for w in threat_words:
                    if w in low_text:
                        return AnalysisResult(category="CATEGORY_A", reason="Признак угроз/насилия", has_links=len(links) > 0, links=links)

                for w in rude_words:
                    if w in low_text:
                        return AnalysisResult(category="CATEGORY_B", reason="Грубость/оскорбление", has_links=len(links) > 0, links=links)

                return AnalysisResult(category="CLEAN", reason="Сообщение соответствует правилам", has_links=len(links) > 0, links=links)
        

        except Exception as e:
            print(f"Error in ModeratorAgent.analyze_message: {e}")
            return AnalysisResult(
                category="ERROR",
                reason=f"Ошибка при анализе: {str(e)}"
            )

    async def close(self):
        await self.client.close()

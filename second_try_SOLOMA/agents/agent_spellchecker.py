"""
Agent: Spellchecker
Checks a message for orthographic/punctuation errors using GigaChat and, if errors
are found, returns a suggested corrected variant and a short explanation.

This agent intentionally uses a small, strict system/user prompt to keep responses
parsable and compact.
"""
from typing import Optional
from gigachat_client import GigachatClient
from config.settings import GIGACHAT_CLIENT_ID, GIGACHAT_AUTH_KEY, GIGACHAT_SCOPE


class SpellCheckResult:
    def __init__(self, has_errors: bool, corrected_text: str = "", details: str = ""):
        self.has_errors = has_errors
        self.corrected_text = corrected_text
        self.details = details


class SpellcheckerAgent:
    def __init__(self):
        self.client = GigachatClient(
            client_id=GIGACHAT_CLIENT_ID,
            auth_key=GIGACHAT_AUTH_KEY,
            scope=GIGACHAT_SCOPE,
        )

    async def check_spelling(self, text: str) -> SpellCheckResult:
        """
        Ask the LLM to check the text for orthographic and punctuation errors.

        Expected compact response formats (the agent will parse them):
        - If no errors: a single line containing NO_ERRORS
        - If errors: start the response with CORRECTED on its own line, then the
          corrected text. Optionally an EXPLANATION section may follow.
        """
        try:
            if not text or not text.strip():
                return SpellCheckResult(False, "", "empty input")

            system_prompt = (
            "Ты — орфографический и пунктуационный корректор русского языка.\n"
            "Твоя задача — исправлять ТОЛЬКО орфографию и пунктуацию.\n"
            "НЕ меняй стиль, лексику, порядок слов и смысл текста.\n"
            "\n"
            "Особое внимание уделяй пунктуации:\n"
            "- обращениям (в начале, середине и конце предложения),\n"
            "- запятым при вводных словах и конструкциях,\n"
            "- запятым в сложных предложениях,\n"
            "- тире, двоеточиям, кавычкам.\n"
            "\n"
            "Если ошибок нет — ответь СТРОГО одной строкой:\n"
            "NO_ERRORS\n"
            "\n"
            "Если ошибки есть — ответь СТРОГО в формате:\n"
            "CORRECTED\n"
            "[исправленный текст]\n"
            "EXPLANATION\n"
            "[краткое объяснение основных правок, 1–2 предложения]\n"
            "\n"
            "Не добавляй комментариев, приветствий или лишнего текста."
        )

            user_message = f"Проверь текст и при необходимости исправь:\n{text}"

            response = await self.client.generate(user_message, system_prompt=system_prompt)

            if not response:
                return SpellCheckResult(False, "", "empty response from LLM")

            # Normalize
            normalized = response.strip()

            if normalized.startswith("NO_ERRORS"):
                return SpellCheckResult(False, "", "no errors")

            if normalized.startswith("CORRECTED"):
                # Try to extract corrected text (between CORRECTED and EXPLANATION)
                body = normalized[len("CORRECTED"):].strip()
                corrected = body
                explanation = ""
                if "EXPLANATION" in body:
                    parts = body.split("EXPLANATION", 1)
                    corrected = parts[0].strip()
                    explanation = parts[1].strip()

                return SpellCheckResult(True, corrected, explanation)

            # Fallback: if response doesn't follow format but seems like corrected text,
            # treat it as correction.
            return SpellCheckResult(True, normalized, "parsed fallback")

        except Exception as e:
            # On any failure, return no-errors=false with message in details
            return SpellCheckResult(False, "", f"error: {e}")

    async def close(self):
        await self.client.close()

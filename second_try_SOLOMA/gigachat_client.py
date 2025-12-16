import aiohttp
import uuid
from urllib.parse import urlencode
from typing import Optional, List

class GigachatClient:
    def __init__(self, client_id, auth_key, scope):
        self.client_id = client_id
        self.auth_key = auth_key      # уже Base64(ClientID:ClientSecret)
        self.scope = scope
        self.access_token = None
        self.session = aiohttp.ClientSession()

    async def authenticate(self):
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

        headers = {
            "Authorization": f"Basic {self.auth_key}",
            "RqUID": str(uuid.uuid4()),  # уникальный ID запроса
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = urlencode({"scope": self.scope})  # правильная форма

        async with self.session.post(url, headers=headers, data=data, ssl=False) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"Token request failed: {resp.status} {text}")
            response = await resp.json()
            self.access_token = response.get("access_token")

    async def generate(self, message: str, system_prompt: Optional[str] = None):
        """
        Генерация текста через GigaChat
        """
        if not self.access_token:
            await self.authenticate()

        url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        payload = {
            "model": "GigaChat",
            "messages": messages
        }

        async with self.session.post(url, headers=headers, json=payload, ssl=False) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise RuntimeError(f"GigaChat error {resp.status}: {data}")
            return data["choices"][0]["message"]["content"]

    async def close(self):
        await self.session.close()

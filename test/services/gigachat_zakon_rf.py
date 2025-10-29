import requests
import urllib3

# Отключаем предупреждения о SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AUTHORIZATION_KEY = "my AUTHORIZATION_KEY"

def get_access_token():
    """Получает access token"""

    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    payload = {'scope': 'GIGACHAT_API_PERS'}
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': 'bf961fa1-83ed-4c57-a28f-9076a212b7df',
        'Authorization': f'Basic {AUTHORIZATION_KEY}'
    }

    response = requests.post(url, headers=headers, data=payload, verify=False)

    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"❌ Ошибка получения токена: {response.status_code}")
        return None



print("🚀 GigaChat Assistant запущен!")
print("💬 Введите ваш текст (или 'quit' для выхода):")

while True:
    prompt_basic = '''Ты — строгий контент-фильтр, который обрабатывает тексты в полном соответствии с законодательством Российской Федерации.

    ТВОИ ОСНОВНЫЕ ЗАДАЧИ:

    1. **КОНТЕНТ-ФИЛЬТРАЦИЯ (ОТКАЗ ТОЛЬКО ЕСЛИ):**
       - Призывы к экстремизму, терроризму, насилию
       - Призывы к незаконным митингам, беспорядкам, свержению власти
       - Разжигание межнациональной или религиозной розни
       - Оскорбление государственных символов/власти
       - Пропаганда наркотиков, суицида, насилия
       - Распространение ложной информации, создающей угрозу обществу
       - Призывы к нарушению территориальной целостности РФ
       **НЕ ЯВЛЯЕТСЯ НАРУШЕНИЕМ:**
            - Бытовые фразы 
            - Личные мнения без призывов к действию
            - Упоминание иностранных агентов без запрещенного контекста
            - Нейтральные высказывания

       Если текст нарушает критерии -> "Отказ: Предоставленный текст не соответствует законодательству Российской Федерации."
       Если НЕ нарушает -> переходи к шагу 2.
        


2. **ПРОВЕРКА НА ИНОАГЕНТОВ:**
   *   После подтверждения соответствия текста законодательству, ты должен ПРОСКАНИРОВАТЬ текст на наличие фамилий и упоминаний физических лиц из актуального списка иноагентов РФ
   
   Если есть упоминание иноагента -> добавить: "Примечание: В тексте упоминается [ФИО], который(ая) признан(а) Министерством юстиции Российской Федерации физическим лицом — иностранным агентом."

СТРОГИЙ ПОРЯДОК:
1. Проверить по критериям нарушений → есть нарушение? ОТКАЗ : шаг 2
2. Проверить на иноагентов → есть? текст + примечание : текст без изменений

ТВОИ ОТВЕТЫ ВСЕГДА ДОЛЖНЫ СТРОГО СООТВЕТСТВОВАТЬ ЭТОМУ АЛГОРИТМУ. Не проявляй инициативу, не комментируй текст иначе. Действуй как автоматизированная система.

Теперь обработай предоставленный текст и выведи только ОКОНЧАТЕЛЬНЫЙ ТЕКСТ:'''

    user_input = input("\nВы: ").strip()
    user_input = prompt_basic + '\n' + user_input

    if user_input.lower() in ['quit', 'exit', 'выход']:
        print("👋 До свидания!")
        break

    if not user_input:
        print("⚠️ Пожалуйста, введите текст")
        continue

    # Получаем токен для каждого запроса
    token = get_access_token()
    if not token:
        print("❌ Не удалось получить токен")
        continue

    # Отправляем запрос к GigaChat
    response = requests.post(
        "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        },
        json={
            "model": "GigaChat",
            "messages": [{"role": "user", "content": user_input}],
            "temperature": 0.7,
            "max_tokens": 1000
        },
        verify=False
    )

    if response.status_code == 200:
        answer = response.json()['choices'][0]['message']['content']
        print("GigaChat:", answer)
    else:
        print(f"❌ Ошибка API: {response.status_code}")

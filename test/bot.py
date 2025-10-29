import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers.commands import start_command, analyze_command
from handlers.message import MessageHandler1
from handlers.errors import error_handler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не установлен")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Инициализируем обработчики
    message_handler = MessageHandler1()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler.handle_message)
    )
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    print("🤖 Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()

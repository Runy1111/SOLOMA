import logging
from telegram import Update
from telegram.ext import ContextTypes

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logging.error("Исключение при обработке обновления:", exc_info=context.error)
    
    if update and update.message:
        try:
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке сообщения. "
                "Попробуйте еще раз или обратитесь к администратору."
            )
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение об ошибке: {e}")

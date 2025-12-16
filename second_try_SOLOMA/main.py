"""
Main bot file with message processing and handlers
"""
import asyncio
import logging
import sys
from datetime import datetime
from agents.corrector_adapter import correct_with_adapter
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
# Очистка кэша импортов для надёжности (временно, для отладки)
import sys
if 'agents.agent_corrector' in sys.modules:
    del sys.modules['agents.agent_corrector']
if 'agents.corrector_adapter' in sys.modules:
    del sys.modules['agents.corrector_adapter']
    
from agents.corrector_adapter import correct_with_adapter

from config.settings import (
    TELEGRAM_TOKEN,
    MAX_VIOLATIONS_FOR_BAN,
    LOG_FILE,
)
from agents.agent_moderator import ModeratorAgent
from agents.agent_alternatives import AlternativesAgent
from agents.agent_corrector import CorrectorAgent
from agents.agent_spam_detector import SpamDetectorAgent
from agents.agent_spellchecker import SpellcheckerAgent
from storage.storage import Storage
from utils.logger import setup_logging

# Setup logging
logger = setup_logging(LOG_FILE)


class ModerationBot:
    def __init__(self):
        self.moderator = ModeratorAgent()
        self.alternatives = AlternativesAgent()
        self.corrector = CorrectorAgent()
        self.spellchecker = SpellcheckerAgent()
        self.spam_detector = SpamDetectorAgent()
        self.storage = Storage()
        self.app = None
        logger.info("Bot initialized")

    async def process_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Main message processing pipeline:
        1. Check spam (Agent 4)
        2. Moderate content (Agent 1)
        3. Handle based on category
        """
        try:
            if not update.message or not update.message.text:
                return

            user_id = update.message.from_user.id
            chat_id = update.message.chat_id
            message_text = update.message.text
            message_id = update.message.message_id

            # Check if user is banned
            if self.storage.is_banned(user_id):
                await update.message.reply_text(
                    f"❌ Вы заблокированы в этом чате.\n"
                    f"Причина: {self.storage.get_ban_reason(user_id)}"
                )
                return

            logger.info(f"User {user_id} in chat {chat_id}: {message_text[:50]}")

            # Step 1: Check spam
            is_spam = await self.spam_detector.check_spam(message_text, user_id)
            if is_spam.is_spam:
                logger.warning(f"Spam detected from user {user_id}: {is_spam.similarity_score:.2%}")
                await update.message.reply_text(
                    f"⚠️ Ваше сообщение похоже на спам (сходство: {is_spam.similarity_score:.1%}).\n"
                    f"Пожалуйста, не повторяйте одни и те же сообщения."
                )
                return

            # Step 2: Analyze content
            analysis = await self.moderator.analyze_message(message_text)

            # Step 2.5: Spellcheck (only if moderator marked CLEAN or CATEGORY_C)
            try:
                if analysis and analysis.category in ("CLEAN", "CATEGORY_C"):
                    spell = await self.spellchecker.check_spelling(message_text)
                    if spell and spell.has_errors:
                        # Send a gentle visible suggestion referencing the original message
                        try:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=(
                                    "⚠️ В вашем сообщении найдены орфографические или пунктуационные ошибки.\n\n"
                                    f"Предлагаемый вариант:\n{spell.corrected_text}"
                                ),
                                reply_to_message_id=message_id,
                            )
                        except Exception as e:
                            logger.error(f"Error sending spellcheck suggestion: {e}")
            except Exception as e:
                logger.error(f"Spellchecker error: {e}")
            
            # Add to history
            self.spam_detector.add_message(message_text, user_id)
            self.storage.add_message(user_id, message_id, message_text, chat_id)

            # Step 3: Handle based on category
            print(analysis.category)
            if analysis.category == "CATEGORY_A":
                await self._handle_category_a(update, context, user_id, analysis)
            elif analysis.category == "CATEGORY_B":
                await self._handle_category_b(update, context, user_id, analysis)
            elif analysis.category == "CATEGORY_C":
                # Special handling for mentions of registered inoagents
                logger.info(f"Category C (inoagent mention) detected for user {user_id}: {analysis.reason}")
                try:
                    # Send a visible reply in the same chat, referencing the original message
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="Сообщение содержит упоминание лица, признанного иноагентом на территории РФ",
                        reply_to_message_id=message_id,
                    )
                except Exception as e:
                    logger.error(f"Error sending CATEGORY_C message: {e}")
            elif analysis.has_links:
                await self._handle_links(update, context, analysis)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await update.message.reply_text("❌ Произошла ошибка при обработке сообщения.")

    async def _handle_category_a(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 user_id: int, analysis):
        """Handle serious violations (Category A)"""
        try:
            # Add violation
            violation_count = self.storage.add_violation(user_id, "CATEGORY_A", analysis.reason)
            logger.warning(f"Category A violation from user {user_id}: {analysis.reason}")

            # Delete message
            try:
                await update.message.delete()
            except Exception as e:
                logger.error(f"Could not delete message: {e}")

            # Send personal warning
            warning_msg = (
                f"⛔ Ваше сообщение было удалено модератором.\n\n"
                f"**Причина:** {analysis.reason}\n\n"
                f"**Всего нарушений:** {violation_count}/{MAX_VIOLATIONS_FOR_BAN}\n\n"
            )

            if violation_count >= MAX_VIOLATIONS_FOR_BAN:
                # Ban user
                self.storage.ban_user(user_id, f"Лимит нарушений ({MAX_VIOLATIONS_FOR_BAN}) превышен")
                warning_msg += f"⛔ Вы заблокированы в этом чате за повторные нарушения."
                logger.info(f"User {user_id} banned after {violation_count} violations")
            else:
                remaining = MAX_VIOLATIONS_FOR_BAN - violation_count
                warning_msg += f"⚠️ Осталось предупреждений: {remaining}"

            await context.bot.send_message(
                chat_id=user_id,
                text=warning_msg,
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Error in _handle_category_a: {e}")

    async def _handle_category_b(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                 user_id: int, analysis):
        """Handle minor violations (Category B)"""
        try:
            # Add violation (but don't delete message)
            violation_count = self.storage.add_violation(user_id, "CATEGORY_B", analysis.reason)
            logger.info(f"Category B violation from user {user_id}: {analysis.reason}")

            # Send public warning with correction button
            keyboard = [
                [InlineKeyboardButton("✏️ Исправить с помощью Корректора", 
                                    callback_data=f"correct_{update.message.message_id}_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            response = (
                f"@{update.message.from_user.username or update.message.from_user.first_name}, "
                f"ваше сообщение содержит {analysis.reason.lower()}.\n\n"
                f"Вы можете его отредактировать с помощью кнопки ниже."
            )


            await update.message.reply_text(response, reply_markup=reply_markup)

            # Если есть ссылки, обработать их через agent_alternatives
            if analysis.has_links and analysis.links:
                await self._handle_links(update, context, analysis)

        except Exception as e:
            logger.error(f"Error in _handle_category_b: {e}")

    async def _handle_links(self, update: Update, context: ContextTypes.DEFAULT_TYPE, analysis):
        """Handle messages with links"""
        try:
            logger.info(f"Links detected: {analysis.links}")

            # Send warning about links
            keyboard = [
                [InlineKeyboardButton("🔍 Посмотреть доступные аналоги",
                                    callback_data=f"alternatives_{analysis.links[0]}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            response = (
                f"🔗 Ссылка в вашем сообщении ведет на ресурс, который может быть "
                f"заблокирован в некоторых регионах.\n\n"
                f"Вы можете посмотреть доступные аналоги."
            )

            await update.message.reply_text(response, reply_markup=reply_markup)

        except Exception as e:
            logger.error(f"Error in _handle_links: {e}")

    async def handle_correct_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle correction button"""
        try:
            query = update.callback_query
            await query.answer()

            data_parts = query.data.split('_')
            if len(data_parts) < 3:
                return

            user_id = int(data_parts[2])
            
            messages = self.storage.get_user_messages(user_id, limit=1)
            if not messages:
                await query.edit_message_text("❌ Не удалось найти исходное сообщение.")
                return

            original_text = messages[-1]['text']

            # Исправление текста через синхронный адаптер
            import asyncio
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                correct_with_adapter,
                self.corrector,
                original_text
            )

            if result.success:
                response = (
                    "Исправленный вариант сообщения:\n\n"
                    f"{result.corrected_text}\n\n"
                    "Вы можете скопировать этот текст и отправить его."
                )
            else:
                response = f"❌ {result.message}"

            await query.edit_message_text(response)

        except Exception as e:
            logger.error(f"Error in handle_correct_callback: {e}")
            await query.edit_message_text("❌ Произошла ошибка при исправлении текста.")

    async def handle_alternatives_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle alternatives button"""
        try:
            query = update.callback_query
            await query.answer()

            # Extract URL from callback data
            url = '_'.join(query.data.split('_')[1:])

            # Find alternatives
            result = await self.alternatives.find_alternatives(url)

            response = f"📂 **Тип контента:** {result.content_type}\n\n**Доступные аналоги:**\n"
            for alt in result.alternatives[:5]:  # Limit to 5
                response += f"\n• **{alt['name']}** - {alt['description']}"

            await query.edit_message_text(response, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in handle_alternatives_callback: {e}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command"""
        await update.message.reply_text(
            "👋 Добро пожаловать в модерируемый чат!\n\n"
            "Я - модератор, который следит за качеством обсуждений.\n\n"
            "📋 Мои команды:\n"
            "/start - Показать это сообщение\n"
            "/help - Помощь\n"
            "/status - Ваш статус в чате\n"
            "/unban <user_id> - Разбанить пользователя (только администраторы)"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        await update.message.reply_text(
            "📚 **Справка по модерации:**\n\n"
            "**Категория А (Серьёзные нарушения):**\n"
            "• Прямые оскорбления\n"
            "• Разжигание ненависти\n"
            "• Экстремизм\n"
            "→ Сообщение удаляется, выдается предупреждение\n\n"
            "**Категория Б (Лёгкие нарушения):**\n"
            "• Ненормативная лексика\n"
            "• Грубость\n"
            "→ Сообщение остается, предлагается исправление\n\n"
            "**Ссылки:**\n"
            "→ Предлагаются легальные аналоги",
            parse_mode="Markdown"
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """User status command"""
        try:
            user_id = update.message.from_user.id
            
            if self.storage.is_banned(user_id):
                status = f"❌ **Статус:** Заблокирован\n**Причина:** {self.storage.get_ban_reason(user_id)}"
            else:
                violations = self.storage.get_violation_count(user_id)
                remaining = MAX_VIOLATIONS_FOR_BAN - violations
                status = (
                    f"✅ **Статус:** Активен\n"
                    f"**Нарушений:** {violations}/{MAX_VIOLATIONS_FOR_BAN}\n"
                    f"**Осталось предупреждений:** {remaining}"
                )

            await update.message.reply_text(status, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error in status_command: {e}")

    async def is_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is chat administrator"""
        try:
            if not update.message or not update.message.chat:
                return False
            
            member = await context.bot.get_chat_member(
                update.message.chat.id,
                update.message.from_user.id
            )
            
            is_admin = member.status in ["administrator", "creator"]
            return is_admin
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return False

    async def unban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Unban user command (admin only)"""
        try:
            # Check admin status
            if not await self.is_admin(update, context):
                await update.message.reply_text(
                    "❌ Эта команда доступна только администраторам!"
                )
                return
            
            # Get target user ID from command arguments
            if not context.args or len(context.args) < 1:
                await update.message.reply_text(
                    "❌ Использование: /unban <user_id>\n\n"
                    "Пример: /unban 12345"
                )
                return
            
            try:
                target_user_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text(
                    f"❌ '{context.args[0]}' - некорректный ID пользователя"
                )
                return
            
            # Check if user is banned
            if not self.storage.is_banned(target_user_id):
                await update.message.reply_text(
                    f"⚠️ Пользователь {target_user_id} не заблокирован"
                )
                return
            
            # Get ban reason before unbanning
            ban_reason = self.storage.get_ban_reason(target_user_id)
            
            # Unban user
            self.storage.unban_user(target_user_id)
            self.storage.clear_violations(target_user_id)
            
            admin_name = update.message.from_user.username or update.message.from_user.first_name
            log_msg = f"👤 Администратор {admin_name} разбанил пользователя {target_user_id}\n"
            log_msg += f"   Причина бана была: {ban_reason}"
            logger.info(log_msg)
            
            await update.message.reply_text(
                f"✅ **Пользователь {target_user_id} разбанен**\n\n"
                f"📋 Была причина: {ban_reason}\n"
                f"🔄 Нарушения очищены",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error in unban_command: {e}")
            await update.message.reply_text(
                "❌ Ошибка при разбане пользователя"
            )

    def setup_handlers(self):
        """Setup all handlers"""
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("unban", self.unban_command))
        
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_message))
        
        self.app.add_handler(CallbackQueryHandler(self.handle_correct_callback, pattern="^correct_"))
        self.app.add_handler(CallbackQueryHandler(self.handle_alternatives_callback, pattern="^alternatives_"))

    def run(self):
        """Run the bot"""
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()
        
        logger.info("Bot is running...")
        self.app.run_polling()

    def stop(self):
        """Stop the bot (cleanup)"""
        try:
            # Close GigaChat sessions (synchronously if possible)
            pass
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        logger.info("Bot stopped")


if __name__ == "__main__":
    import sys
    
    bot = ModerationBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

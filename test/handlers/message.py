import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from analyzers.multi_level import MultiLevelAnalyzer
from config import RISK_LEVELS

class MessageHandler1:
    """Обработчик сообщений"""
    
    def __init__(self):
        self.analyzer = MultiLevelAnalyzer()
        self.user_warnings = {}
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка входящих сообщений"""
        user_text = update.message.text
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        if user_text.startswith('/'):
            return
        
        # Комплексный анализ
        analysis = await self.analyzer.analyze(user_text, chat_id, user_id)

        # Удаляем сообщение сразу, если оценка риска очень высокая
        if analysis.final_score >= 0.9:
            try:
                await update.message.delete()
                logging.info(f"Сообщение удалено по порогу score>=0.9: chat={chat_id}, user={user_id}, score={analysis.final_score}")
            except Exception as e:
                logging.error(f"Ошибка удаления сообщения по порогу score>=0.9: {e}")
            return
        
        # Действия в зависимости от уровня риска
        if analysis.risk_level == 'critical':
            await self._handle_critical_violation(update, analysis)
        elif analysis.risk_level == 'high':
            await self._handle_high_risk(update, analysis)
        elif analysis.risk_level == 'medium' and analysis.final_score > 0.7:
            await self._handle_medium_risk(update, analysis)
        
        # Логирование
        self._log_analysis(chat_id, user_id, analysis)
    
    async def _handle_critical_violation(self, update: Update, analysis):
        """Обработка критических нарушений"""
        message = "🚨 *НАРУШЕНИЕ ЗАКОНОДАТЕЛЬСТВА РФ* 🚨\n\n"
        
        for violation in analysis.rkn_violations:
            message += f"• Запрещенный ресурс: {violation.domain}\n"
            if violation.reason:
                message += f"  Причина: {violation.reason}\n"
        
        message += "\n_Сообщение удалено. Повторные нарушения приведут к блокировке._"
        
        try:
            await update.message.delete()
            warning_msg = await update.message.reply_text(message, parse_mode='Markdown')
            await asyncio.sleep(30)
            await warning_msg.delete()
        except Exception as e:
            logging.error(f"Ошибка удаления сообщения: {e}")
    
    async def _handle_high_risk(self, update: Update, analysis):
        """Обработка высокого риска"""
        message = "⚠️ *КОНТЕКСТНОЕ УПОМИНАНИЕ ЗАПРЕЩЕННОГО КОНТЕНТА* ⚠️\n\n"
        
        for violation in analysis.contextual_violations:
            message += f"• {violation.reason}\n"
        
        message += "\n_Упоминание заблокированных ресурсов запрещено._"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def _handle_medium_risk(self, update: Update, analysis):
        """Обработка среднего риска"""
        risk_emoji = RISK_LEVELS.get(analysis.risk_level, '⚪️')
        await update.message.reply_text(
            f"{risk_emoji} *Внимание:* Потенциально опасный контент\n"
            f"Оценка: {analysis.final_score:.1%}",
            parse_mode='Markdown'
        )
    
    def _log_analysis(self, chat_id: int, user_id: int, analysis):
        """Логирование результатов анализа"""
        logging.info(
            f"Анализ: chat={chat_id}, user={user_id}, "
            f"risk={analysis.risk_level}, score={analysis.final_score:.3f}, "
            f"type={analysis.analysis_type}"
        )

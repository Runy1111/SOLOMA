from telegram import Update
from telegram.ext import ContextTypes
from analyzers.multi_level import MultiLevelAnalyzer

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = """
🤖 *Бот-анализатор экстремистского контента*

Я проверяю сообщения на:
• Нарушения законодательства РФ (РКН)
• Контекстные упоминания запрещенных ресурсов  
• Экстремистский контент

*Команды:*
/analyze <текст> - детальный анализ текста

Просто отправь мне сообщение для анализа!
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /analyze"""
    user_text = ' '.join(context.args)
    
    if not user_text:
        await update.message.reply_text(
            "Укажите текст для анализа: `/analyze ваш текст`", 
            parse_mode='Markdown'
        )
        return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    analyzer = MultiLevelAnalyzer()
    analysis = await analyzer.analyze(user_text, chat_id, user_id)
    
    response = f"📊 *Анализ текста:*\n`{user_text}`\n\n"
    response += f"*Общий риск:* {analysis.risk_level.upper()}\n"
    response += f"*Оценка:* {analysis.final_score:.1%}\n"
    response += f"*Тип анализа:* {analysis.analysis_type}\n"
    
    if analysis.rkn_violations:
        response += "\n*Нарушения РКН:*\n"
        for violation in analysis.rkn_violations:
            response += f"• {violation.domain}\n"
    
    if analysis.contextual_violations:
        response += "\n*Контекстные нарушения:*\n"
        for violation in analysis.contextual_violations:
            response += f"• {violation.reason}\n"
    
    await update.message.reply_text(response, parse_mode='Markdown')

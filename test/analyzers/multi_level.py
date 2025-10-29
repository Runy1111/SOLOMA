import logging
from typing import Dict
from models.analysis import AnalysisResult
from services.deepseek import DeepSeekAnalyzer
from services.context_tracker import ContextualMentionTracker
from analyzers.heuristic import HeuristicAnalyzer
from config import ANALYSIS_CONFIG

class MultiLevelAnalyzer:
    """Многоуровневый анализатор контента"""
    
    def __init__(self):
        self.deepseek = DeepSeekAnalyzer()
        self.heuristic = HeuristicAnalyzer()
        self.context_tracker = ContextualMentionTracker()
        self.config = ANALYSIS_CONFIG
    
    async def analyze(self, text: str, chat_id: int, user_id: int) -> AnalysisResult:
        """Комплексный анализ сообщения"""
        
        # Уровень 1: Проверка РКН через AntiZapret
        rkn_result = await self._check_rkn_violations(text, chat_id, user_id)
        if rkn_result['violations']:
            return self._create_rkn_violation_result(rkn_result)
        
        # Уровень 2: Контекстные упоминания
        context_violations = self.context_tracker.check_contextual_reference(text, chat_id)
        if context_violations:
            return self._create_context_violation_result(context_violations)
        
        # Уровень 3: Быстрые эвристики
        heuristic_score = self.heuristic.analyze(text)
        if heuristic_score < self.config['fast_check_threshold']:
            return AnalysisResult(
                risk_level='low',
                final_score=heuristic_score,
                rkn_violations=[],
                contextual_violations=[],
                analysis_type='heuristic'
            )
        
        # Уровень 4: LLM анализ для сложных случаев
        if heuristic_score > self.config['deep_analysis_threshold']:
            return await self._perform_deep_analysis(text, heuristic_score)
        
        return AnalysisResult(
            risk_level='medium',
            final_score=heuristic_score,
            rkn_violations=[],
            contextual_violations=[],
            analysis_type='heuristic'
        )
    
    async def _check_rkn_violations(self, text: str, chat_id: int, user_id: int) -> Dict:
        """Проверка нарушений РКН"""
        # Убираем все обращения к внешнему сервису AntiZapret.
        # По умолчанию не считаем домены заблокированными — возвращаем пустой список нарушений,
        # но оставляем список проверенных доменов для возможной последующей логики.
        violations = []
        domains = self.heuristic.extract_domains(text)

        # Раньше здесь выполнялся внешний запрос в AntiZapret; теперь этот шаг опущен.
        return {'violations': violations, 'domains_checked': domains}
    
    async def _perform_deep_analysis(self, text: str, heuristic_score: float) -> AnalysisResult:
        """Глубокий анализ через LLM"""
        llm_result = await self.deepseek.analyze_toxicity(text)
        
        final_score = max(heuristic_score, llm_result.get('toxicity_score', 0))
        risk_level = llm_result.get('risk_level', 'medium')
        
        actions = []
        if final_score > self.config['critical_threshold']:
            actions = ['warn_user']
        
        return AnalysisResult(
            risk_level=risk_level,
            final_score=final_score,
            rkn_violations=[],
            contextual_violations=[],
            llm_analysis=llm_result,
            actions=actions,
            analysis_type='deep_llm'
        )
    
    def _create_rkn_violation_result(self, rkn_result: Dict) -> AnalysisResult:
        """Создает результат для нарушений РКН"""
        return AnalysisResult(
            risk_level='critical',
            final_score=1.0,
            rkn_violations=rkn_result['violations'],

            contextual_violations=[],
            actions=['delete_message', 'warn_user', 'report_to_admins'],
            analysis_type='rkn_check'
        )
    
    def _create_context_violation_result(self, context_violations: list) -> AnalysisResult:
        """Создает результат для контекстных нарушений"""
        return AnalysisResult(
            risk_level='high',
            final_score=0.8,
            rkn_violations=[],
            contextual_violations=context_violations,
            actions=['warn_user', 'notify_moderators'],
            analysis_type='context_check'
        )

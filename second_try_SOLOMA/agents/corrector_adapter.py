from dataclasses import dataclass
from .agent_corrector import CorrectorAgent


@dataclass
class CorrectionResult:
    success: bool
    corrected_text: str
    message: str = ""


def correct_with_adapter(corrector, text):
    try:
        result = corrector.correct(text)
        corrected = result.text.strip()
        original = text.strip()
        
        if not corrected or corrected == original:
            return CorrectionResult(
                success=False,
                corrected_text=text,
                message="Текст не требует исправлений"
            )
        
        return CorrectionResult(
            success=True,
            corrected_text=corrected
        )
    
    except Exception as e:
        return CorrectionResult(
            success=False,
            corrected_text=text,
            message="Ошибка корректора: " + str(e)
        )
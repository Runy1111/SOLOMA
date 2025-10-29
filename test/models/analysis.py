from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class RKNViolation:
    domain: str
    blocked: bool
    decision: Optional[str] = None
    reason: Optional[str] = None
    risk_level: str = "low"

@dataclass
class ContextualViolation:
    type: str
    domain: str
    reason: str
    risk_level: str

@dataclass
class AnalysisResult:
    risk_level: str
    final_score: float
    rkn_violations: List[RKNViolation]
    contextual_violations: List[ContextualViolation]
    llm_analysis: Optional[Dict] = None
    actions: List[str] = None
    analysis_type: str = "unknown"
    
    def __post_init__(self):
        if self.actions is None:
            self.actions = []

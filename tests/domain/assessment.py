from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AssessmentEvent:
    event_type: str
    timestamp: str
    step: int = 0
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssessmentPenalty:
    code: str
    message: str
    score_delta: int
    step: int = 0
    timestamp: str = ""


@dataclass
class AssessmentScoreItem:
    code: str
    title: str
    category: str
    status: str
    max_score: int
    earned_score: int
    step: int = 0
    detail: str = ""


@dataclass
class AssessmentResult:
    session_id: str
    scene_id: str
    mode: str
    started_at: str
    finished_at: str
    elapsed_seconds: int
    passed: bool
    total_score: int
    max_score: int
    veto_reason: Optional[str] = None
    step_scores: Dict[str, int] = field(default_factory=dict)
    step_max_scores: Dict[str, int] = field(default_factory=dict)
    score_items: List[AssessmentScoreItem] = field(default_factory=list)
    penalties: List[AssessmentPenalty] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""


@dataclass
class AssessmentSession:
    session_id: str
    scene_id: str
    mode: str
    started_at: str
    fault_selection_mode: str = "specified"
    events: List[AssessmentEvent] = field(default_factory=list)
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    fault_guess_scene_id: str = ""
    fault_guess_submitted: bool = False
    fault_guess_correct: bool = False
    finished_at: Optional[str] = None
    result: Optional[AssessmentResult] = None
    result_shown: bool = False

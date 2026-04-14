from __future__ import annotations

from typing import Optional, Tuple

from domain.assessment import AssessmentPenalty, AssessmentScoreItem


def make_score_item(
    code: str,
    title: str,
    category: str,
    max_score: int,
    earned_score: int,
    step: int = 0,
    detail: str = "",
    penalty_message: str = "",
) -> Tuple[AssessmentScoreItem, Optional[AssessmentPenalty]]:
    earned_score = max(0, min(max_score, earned_score))
    if earned_score >= max_score:
        status = "通过"
    elif earned_score <= 0:
        status = "未通过"
    else:
        status = "部分扣分"

    item = AssessmentScoreItem(
        code=code,
        title=title,
        category=category,
        status=status,
        max_score=max_score,
        earned_score=earned_score,
        step=step,
        detail=detail,
    )

    lost_score = max_score - earned_score
    if lost_score > 0 and penalty_message:
        penalty = AssessmentPenalty(
            code=code,
            message=penalty_message,
            score_delta=-lost_score,
            step=step,
        )
        return item, penalty
    return item, None

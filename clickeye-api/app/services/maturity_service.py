import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.maturity_assessment import MaturityAssessment
from app.models.preset import Preset
from app.schemas.preset import MaturityQuestion

QUESTIONS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "presets" / "maturity_questions.json"
)

# 점수 → 성숙도 단계 매핑
LEVEL_THRESHOLDS = [
    (0, 40, "starter"),
    (40, 70, "intermediate"),
    (70, 101, "advanced"),
]


def _load_questions() -> list[MaturityQuestion]:
    """질문지 JSON을 로드하여 Pydantic 모델 리스트로 반환."""
    raw = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    return [MaturityQuestion.model_validate(q) for q in raw]


def _calculate_score(answers: dict[str, int], questions: list[MaturityQuestion]) -> int:
    """가중 평균 스코어링 (0-100)."""
    total_weight = 0.0
    weighted_sum = 0.0

    for q in questions:
        if q.id not in answers:
            continue
        raw_score = answers[q.id]
        # 점수는 0-100 범위로 클램프
        clamped = max(0, min(100, raw_score))
        weighted_sum += clamped * q.weight
        total_weight += q.weight

    if total_weight == 0:
        return 0

    return round(weighted_sum / total_weight)


def _score_to_level(score: int) -> str:
    """점수를 성숙도 단계로 변환."""
    for low, high, level in LEVEL_THRESHOLDS:
        if low <= score < high:
            return level
    return "advanced"


def _build_reasoning(score: int, level: str) -> str:
    """평가 결과에 대한 설명 생성."""
    if level == "starter":
        return (
            f"종합 점수 {score}/100. AI 개발 자동화 도입 초기 단계입니다. "
            "기본 에이전트와 단순 파이프라인으로 시작하는 것을 권장합니다."
        )
    if level == "intermediate":
        return (
            f"종합 점수 {score}/100. 개발 프로세스가 어느 정도 정립되어 있습니다. "
            "멀티 에이전트 협업과 자동화된 코드 리뷰를 도입할 수 있습니다."
        )
    return (
        f"종합 점수 {score}/100. 성숙한 개발 환경을 갖추고 있습니다. "
        "전체 SDLC에 걸친 AI 자동화와 고급 품질 게이트를 활용할 수 있습니다."
    )


class MaturityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def get_questions(self) -> list[MaturityQuestion]:
        return _load_questions()

    async def get_latest_assessment(self, user_id: UUID) -> MaturityAssessment | None:
        """해당 유저의 가장 최근 성숙도 평가를 반환한다. 없으면 None."""
        from sqlalchemy import desc
        stmt = (
            select(MaturityAssessment)
            .where(MaturityAssessment.user_id == user_id)
            .order_by(desc(MaturityAssessment.created_at))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def assess(
        self,
        user_id: UUID,
        answers: dict[str, int],
        organization_id: UUID | None = None,
    ) -> dict:
        """성숙도 평가를 수행하고 결과를 저장한다."""
        questions = _load_questions()
        score = _calculate_score(answers, questions)
        level = _score_to_level(score)
        reasoning = _build_reasoning(score, level)

        # 해당 레벨의 추천 프리셋 조회
        preset_stmt = select(Preset).where(
            Preset.maturity_level == level,
            Preset.is_system.is_(True),
            Preset.is_active.is_(True),
        )
        preset_result = await self.db.execute(preset_stmt)
        recommended_preset = preset_result.scalars().first()

        recommended_preset_id = recommended_preset.id if recommended_preset else None

        # 평가 결과 저장
        assessment = MaturityAssessment(
            user_id=user_id,
            organization_id=organization_id,
            answers=answers,
            score=score,
            level=level,
            recommended_preset_id=recommended_preset_id,
        )
        self.db.add(assessment)
        await self.db.commit()

        return {
            "level": level,
            "score": score,
            "recommended_preset_id": recommended_preset_id,
            "reasoning": reasoning,
        }

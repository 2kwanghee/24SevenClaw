"""마스터 PM AI 오케스트레이터 서비스.

8가지 핵심 기능:
1. 작업 분해 및 배정
2. 프롬프트 표준화
3. 결과 통합 및 비교
4. 충돌 해결
5. 리스크 탐지
6. 보고 자동화
7. 버전 관리
8. 단계 전이 판단

10단계 프로세스: 요청→분해→배정→초안→리뷰→통합→검증→승인→전이→완료
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.orchestrator import OrchestratorSession, PhaseEvent, SubTask
from app.schemas.orchestrator import (
    AssignRequest,
    DecomposeRequest,
    PhaseTransitionRequest,
    SessionCreate,
    SubTaskCreate,
    SubTaskUpdate,
)
from app.services.artifact_service import ArtifactService
from app.services.claude_service import ClaudeService

logger = logging.getLogger(__name__)

# 단계 전이 맵 (contracts와 동기화)
ORCHESTRATOR_TRANSITIONS: dict[str, list[str]] = {
    "requested": ["decomposed"],
    "decomposed": ["assigned"],
    "assigned": ["drafting"],
    "drafting": ["reviewing"],
    "reviewing": ["integrating", "drafting"],
    "integrating": ["validating"],
    "validating": ["approved", "integrating"],
    "approved": ["transitioning"],
    "transitioning": ["completed"],
    "completed": [],
}

# 역할별 키워드 매칭 (작업 분해 시 자동 배정)
ROLE_KEYWORDS: dict[str, list[str]] = {
    "architect": ["설계", "아키텍처", "구조", "design", "architecture", "system"],
    "frontend": ["UI", "컴포넌트", "페이지", "프론트", "component", "react", "css"],
    "backend": ["API", "서버", "엔드포인트", "데이터베이스", "서비스", "endpoint", "db"],
    "qa": ["테스트", "검증", "품질", "test", "validation", "coverage"],
    "security": ["보안", "인증", "권한", "취약점", "security", "auth", "vulnerability"],
    "devops": ["배포", "인프라", "CI/CD", "도커", "deploy", "docker", "infrastructure"],
    "reviewer": ["리뷰", "검토", "코드리뷰", "review", "code review"],
}

# 리스크 키워드 탐지
RISK_KEYWORDS: dict[str, str] = {
    "보안": "security_risk",
    "security": "security_risk",
    "삭제": "data_loss_risk",
    "delete": "data_loss_risk",
    "마이그레이션": "migration_risk",
    "migration": "migration_risk",
    "프로덕션": "production_risk",
    "production": "production_risk",
    "성능": "performance_risk",
    "performance": "performance_risk",
    "breaking": "breaking_change_risk",
    "호환": "compatibility_risk",
}


class OrchestratorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # === 세션 관리 ===

    async def create_session(
        self, project_id: UUID, user_id: UUID, data: SessionCreate
    ) -> OrchestratorSession:
        risk_flags = self._detect_risks(data.title, data.description)
        session = OrchestratorSession(
            project_id=project_id,
            title=data.title,
            description=data.description,
            phase="requested",
            created_by=user_id,
            risk_flags=risk_flags,
        )
        self.db.add(session)
        await self.db.flush()  # session.id 확정

        # 초기 단계 이벤트 기록
        event = PhaseEvent(
            session_id=session.id,
            old_phase=None,
            new_phase="requested",
            actor_type="user",
            actor_id=user_id,
            message="세션 생성",
        )
        self.db.add(event)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: UUID) -> OrchestratorSession:
        session = await self.db.get(OrchestratorSession, session_id)
        if session is None:
            raise AppError("SESSION_NOT_FOUND", "오케스트레이션 세션을 찾을 수 없습니다.", 404)
        return session

    async def list_sessions(
        self,
        project_id: UUID,
        offset: int = 0,
        limit: int = 20,
        phase_filter: str | None = None,
    ) -> tuple[list[OrchestratorSession], int]:
        conditions = [OrchestratorSession.project_id == project_id]
        if phase_filter:
            conditions.append(OrchestratorSession.phase == phase_filter)

        count_stmt = (
            select(func.count()).select_from(OrchestratorSession).where(*conditions)
        )
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            select(OrchestratorSession)
            .where(*conditions)
            .order_by(OrchestratorSession.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        sessions = list(result.scalars().all())
        return sessions, total

    # === 1. 작업 분해 ===

    async def decompose(
        self, session_id: UUID, data: DecomposeRequest
    ) -> tuple[OrchestratorSession, list[SubTask]]:
        session = await self.get_session(session_id)
        if session.phase != "requested":
            raise AppError(
                "INVALID_PHASE",
                f"작업 분해는 'requested' 단계에서만 가능합니다. 현재: '{session.phase}'",
                422,
            )

        # Claude로 지능형 분해 시도 → 실패 시 키워드 폴백
        subtasks = await self._generate_subtasks_with_claude(session, data.hints)
        for st in subtasks:
            self.db.add(st)
        await self.db.flush()  # subtask.id 확정 (depends_on 참조용)

        # 프롬프트 표준화 (기능 2)
        session.prompt_template = self._build_prompt_template(session, subtasks)

        # 단계 전이
        await self._transition_phase(session, "decomposed", "system", message="작업 분해 완료")

        await self.db.commit()
        await self.db.refresh(session)
        for st in subtasks:
            await self.db.refresh(st)
        return session, subtasks

    # === 2. AI 팀 배정 ===

    async def assign(
        self, session_id: UUID, data: AssignRequest
    ) -> tuple[OrchestratorSession, list[SubTask]]:
        session = await self.get_session(session_id)
        if session.phase != "decomposed":
            raise AppError(
                "INVALID_PHASE",
                f"팀 배정은 'decomposed' 단계에서만 가능합니다. 현재: '{session.phase}'",
                422,
            )

        subtasks = await self._get_subtasks(session_id)
        if not subtasks:
            raise AppError("NO_SUBTASKS", "분해된 서브태스크가 없습니다.", 422)

        # 수동 오버라이드 적용
        if data.overrides:
            for st in subtasks:
                override_role = data.overrides.get(str(st.id))
                if override_role:
                    st.assigned_role = override_role

        # 단계 전이
        await self._transition_phase(session, "assigned", "system", message="AI 팀 배정 완료")

        await self.db.commit()
        await self.db.refresh(session)
        for st in subtasks:
            await self.db.refresh(st)
        return session, subtasks

    # === 단계 전이 (기능 8) ===

    async def transition(
        self,
        session_id: UUID,
        data: PhaseTransitionRequest,
        actor_type: str = "user",
        actor_id: UUID | None = None,
    ) -> tuple[OrchestratorSession, PhaseEvent]:
        session = await self.get_session(session_id)
        event = await self._transition_phase(
            session, data.target_phase, actor_type, actor_id, data.message
        )
        await self.db.commit()
        await self.db.refresh(session)
        await self.db.refresh(event)
        return session, event

    # === 서브태스크 관리 ===

    async def create_subtask(
        self, session_id: UUID, data: SubTaskCreate
    ) -> SubTask:
        await self.get_session(session_id)
        subtask = SubTask(
            session_id=session_id,
            title=data.title,
            description=data.description,
            assigned_role=data.assigned_role,
            order_index=data.order_index,
            depends_on=data.depends_on or [],
            artifact_id=data.artifact_id,
        )
        self.db.add(subtask)
        await self.db.commit()
        await self.db.refresh(subtask)
        return subtask

    async def update_subtask(
        self, subtask_id: UUID, data: SubTaskUpdate
    ) -> SubTask:
        subtask = await self.db.get(SubTask, subtask_id)
        if subtask is None:
            raise AppError("SUBTASK_NOT_FOUND", "서브태스크를 찾을 수 없습니다.", 404)

        if data.status is not None:
            subtask.status = data.status
        if data.result_summary is not None:
            subtask.result_summary = data.result_summary
        if data.artifact_id is not None:
            subtask.artifact_id = data.artifact_id
        subtask.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(subtask)
        return subtask

    async def get_subtasks(self, session_id: UUID) -> list[SubTask]:
        await self.get_session(session_id)
        return await self._get_subtasks(session_id)

    # === 이력 조회 ===

    async def get_phase_history(self, session_id: UUID) -> list[PhaseEvent]:
        await self.get_session(session_id)
        stmt = (
            select(PhaseEvent)
            .where(PhaseEvent.session_id == session_id)
            .order_by(PhaseEvent.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # === 리스크 탐지 (기능 5) ===

    async def detect_risks(self, session_id: UUID) -> list[str]:
        session = await self.get_session(session_id)
        subtasks = await self._get_subtasks(session_id)

        risks = list(session.risk_flags) if session.risk_flags else []
        for st in subtasks:
            st_risks = self._detect_risks(st.title, st.description)
            for r in st_risks:
                if r not in risks:
                    risks.append(r)

        session.risk_flags = risks
        session.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(session)
        return risks

    # === 보고 자동화 (기능 6) ===

    async def get_summary(
        self, session_id: UUID
    ) -> tuple[OrchestratorSession, list[SubTask], list[PhaseEvent]]:
        session = await self.get_session(session_id)
        subtasks = await self._get_subtasks(session_id)
        history = await self.get_phase_history(session_id)
        return session, subtasks, history

    # === 내부 헬퍼 ===

    async def _get_subtasks(self, session_id: UUID) -> list[SubTask]:
        stmt = (
            select(SubTask)
            .where(SubTask.session_id == session_id)
            .order_by(SubTask.order_index.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _transition_phase(
        self,
        session: OrchestratorSession,
        target_phase: str,
        actor_type: str,
        actor_id: UUID | None = None,
        message: str | None = None,
    ) -> PhaseEvent:
        old_phase = session.phase
        allowed = ORCHESTRATOR_TRANSITIONS.get(old_phase, [])
        if target_phase not in allowed:
            raise AppError(
                "INVALID_TRANSITION",
                f"'{old_phase}' → '{target_phase}' 전이는 허용되지 않습니다. "
                f"허용: {allowed}",
                422,
            )

        session.phase = target_phase
        session.updated_at = datetime.now(UTC)

        event = PhaseEvent(
            session_id=session.id,
            old_phase=old_phase,
            new_phase=target_phase,
            actor_type=actor_type,
            actor_id=actor_id,
            message=message,
        )
        self.db.add(event)

        # approved 전이 시 연결된 Artifact도 자동 approved 전이
        if target_phase == "approved":
            subtasks = await self._get_subtasks(session.id)
            artifact_ids = [
                st.artifact_id for st in subtasks if st.artifact_id is not None
            ]
            if artifact_ids:
                artifact_svc = ArtifactService(self.db)
                await artifact_svc.bulk_transition(
                    artifact_ids=artifact_ids,
                    target_status="approved",
                    actor_type="system",
                    message=f"오케스트레이터 세션 '{session.title}' approved 전이에 의한 자동 갱신",
                )

        return event

    async def _generate_subtasks_with_claude(
        self, session: OrchestratorSession, hints: list[str] | None
    ) -> list[SubTask]:
        """Claude API로 서브태스크를 생성한다. 실패 시 키워드 폴백."""
        try:
            claude = ClaudeService()
            items = await claude.decompose_tasks(
                str(session.title),
                str(session.description) if session.description is not None else None,
                hints,
            )
            if items:
                valid_roles = {
                    "architect", "frontend", "backend", "qa",
                    "security", "devops", "reviewer",
                }
                subtasks: list[SubTask] = []
                for idx, item in enumerate(items):
                    role = item.get("assigned_role", "backend")
                    if role not in valid_roles:
                        role = "backend"
                    st = SubTask(
                        session_id=session.id,
                        title=item.get("title", f"서브태스크 {idx + 1}"),
                        description=item.get("description") or f"[{session.title}] {role} 작업",
                        assigned_role=role,
                        order_index=idx,
                        depends_on=[str(subtasks[idx - 1].id)] if idx > 0 and subtasks else [],
                    )
                    subtasks.append(st)
                return subtasks
        except Exception:
            logger.warning("_generate_subtasks_with_claude: Claude 호출 실패, 키워드 폴백")
        return self._generate_subtasks(session, hints)

    def _generate_subtasks(
        self, session: OrchestratorSession, hints: list[str] | None
    ) -> list[SubTask]:
        """제목과 설명을 분석하여 서브태스크를 자동 생성한다."""
        text = f"{session.title} {session.description or ''}"
        if hints:
            text += " " + " ".join(hints)

        detected_roles: list[str] = []
        for role, keywords in ROLE_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text.lower():
                    if role not in detected_roles:
                        detected_roles.append(role)
                    break

        # 탐지된 역할이 없으면 기본 3단계 (설계→구현→검증)
        if not detected_roles:
            detected_roles = ["architect", "backend", "qa"]

        subtasks: list[SubTask] = []
        role_task_titles: dict[str, str] = {
            "architect": "아키텍처 설계 및 구조 정의",
            "frontend": "프론트엔드 UI 구현",
            "backend": "백엔드 API 및 서비스 구현",
            "qa": "테스트 작성 및 품질 검증",
            "security": "보안 검토 및 취약점 분석",
            "devops": "인프라 구성 및 배포 준비",
            "reviewer": "코드 리뷰 및 최종 검토",
        }

        for idx, role in enumerate(detected_roles):
            subtask = SubTask(
                session_id=session.id,
                title=role_task_titles.get(role, f"{role} 작업"),
                description=f"[{session.title}] {role} 역할 담당 서브태스크",
                assigned_role=role,
                order_index=idx,
                depends_on=[],
            )
            # 첫 번째가 아니면 이전 태스크에 의존
            if idx > 0 and subtasks:
                subtask.depends_on = [str(subtasks[idx - 1].id)]
            subtasks.append(subtask)

        return subtasks

    def _build_prompt_template(
        self, session: OrchestratorSession, subtasks: list[SubTask]
    ) -> str:
        """프롬프트 표준화 (기능 2): 세션 정보를 기반으로 표준 프롬프트 생성."""
        lines = [
            f"# 오케스트레이션 세션: {session.title}",
            "",
            f"## 설명\n{session.description or '없음'}",
            "",
            "## 서브태스크",
        ]
        for st in subtasks:
            lines.append(f"- [{st.assigned_role}] {st.title}")

        if session.risk_flags:
            lines.append("")
            lines.append("## 탐지된 리스크")
            for flag in session.risk_flags:
                lines.append(f"- ⚠️ {flag}")

        return "\n".join(lines)

    def _detect_risks(self, title: str, description: str | None) -> list[str]:
        """리스크 탐지 (기능 5): 키워드 기반 리스크 플래그 추출."""
        text = f"{title} {description or ''}".lower()
        risks: list[str] = []
        for keyword, risk_flag in RISK_KEYWORDS.items():
            if keyword.lower() in text and risk_flag not in risks:
                risks.append(risk_flag)
        return risks

"""정적 코드 분석 + LLM 요약 결과 영속.

ModernizeSession 1건당 1행 (1:1, unique). 분석 pipeline 의 step 2~6 산출물이 여기 모인다.
- step 2 scan: loc_total, file_count, lang_distribution
- step 3 manifest: manifests, framework_signals
- step 4 outdated: outdated_packages, risk_flags
- step 5 sample: (snippets 는 LLM 입력 후 폐기)
- step 6 LLM: llm_summary_md, tokens_used

원본 코드는 step 7 직후 워크스페이스 삭제로 비보관. 분석 메타만 남는다.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    Uuid,
    text,
)

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class CodebaseAnalysis(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "codebase_analyses"

    session_id = Column(
        Uuid,
        ForeignKey("modernize_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    loc_total = Column(Integer, nullable=True)
    file_count = Column(Integer, nullable=True)
    # {"python": 0.62, "typescript": 0.28, ...} — LOC 비중 비율
    lang_distribution = Column(
        JSON, nullable=False, default=dict, server_default=text("'{}'::json")
    )
    # [{"path":"pyproject.toml","kind":"python","raw_deps":{...}}, ...]
    manifests = Column(JSON, nullable=False, default=list, server_default=text("'[]'::json"))
    dep_graph = Column(JSON, nullable=True)
    # [{"name":"django","current":"3.2","latest":"5.0","severity":"high"}, ...]
    outdated_packages = Column(
        JSON, nullable=False, default=list, server_default=text("'[]'::json")
    )
    # {"django": "3.2", "python": "3.8", "node": "16", ...}
    framework_signals = Column(
        JSON, nullable=False, default=dict, server_default=text("'{}'::json")
    )
    # ["python_eol_3_8", "node_eol_16", ...]
    risk_flags = Column(JSON, nullable=False, default=list, server_default=text("'[]'::json"))
    llm_summary_md = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    analyzed_at = Column(DateTime(timezone=True), nullable=True)

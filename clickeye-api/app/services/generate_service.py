"""ZIP 생성 서비스 — 위저드 설정 기반 프로젝트 ZIP 패키징."""

import io
import zipfile
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.catalog import prefetch_for_generator
from app.engine.generator import generate_all
from app.schemas.generate import GenerateRequest


async def generate_zip(
    request: GenerateRequest,
    project_name: str,
    db: AsyncSession | None = None,
    pm_slug: str | None = None,
    pm_markdown: str | None = None,
    pm_compositions: list[dict[str, Any]] | None = None,
    catalog_entry: dict[str, Any] | None = None,
) -> io.BytesIO:
    """위저드 설정 기반 프로젝트 파일을 ZIP으로 패키징하여 BytesIO로 반환.

    API 키(env_vars)는 메모리에서만 처리되며 DB/로그에 기록하지 않음.
    pm_slug/pm_markdown 이 있으면 플랫폼별 PM 파일을 ZIP에 포함한다.
    pm_compositions 이 있으면 composition 에이전트/스킬을 우선 병합한다.
    catalog_entry 가 있으면 CLAUDE.md / PM 파일에 설계 철학·에이전트 컨텍스트를 주입한다.
    """
    engine_project_name = request.solution.get("projectName", project_name)
    project_type = request.solution.get("solutionType", "fullstack")
    stack_id = request.solution.get("stackPreset", "custom")
    agent_ids = request.agents
    workflow_ids = request.skills + request.pipelines
    hook_ids: list[str] = getattr(request, "hook_ids", []) or []
    platform_id = str(request.platform.get("platformId", "claude-code"))

    catalog_prefetch = None
    if db is not None:
        catalog_prefetch = await prefetch_for_generator(
            db, agent_ids=agent_ids, skill_ids=workflow_ids, hook_ids=hook_ids
        )

    files = generate_all(
        project_name=engine_project_name,
        project_type=project_type,
        stack_id=stack_id,
        agent_ids=agent_ids,
        workflow_ids=workflow_ids,
        platform_id=platform_id,
        os_id=getattr(request, "os_id", "wsl2"),
        env_vars=request.env_vars if request.env_vars else None,
        pm_slug=pm_slug,
        pm_markdown=pm_markdown,
        pm_compositions=pm_compositions,
        catalog_entry=catalog_entry,
        catalog_prefetch=catalog_prefetch,
        hook_ids=hook_ids or None,
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(files.items()):
            zf.writestr(path, content)  # str | bytes 모두 허용

    buffer.seek(0)
    return buffer

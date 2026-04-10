"""ZIP 생성 서비스 — 위저드 설정 기반 프로젝트 ZIP 패키징."""

import io
import zipfile

from app.engine.generator import generate_all
from app.schemas.generate import GenerateRequest


def generate_zip(request: GenerateRequest, project_name: str) -> io.BytesIO:
    """위저드 설정 기반 프로젝트 파일을 ZIP으로 패키징하여 BytesIO로 반환.

    API 키(env_vars)는 메모리에서만 처리되며 DB/로그에 기록하지 않음.
    """
    # 위저드 데이터에서 생성 엔진 파라미터 추출
    engine_project_name = request.solution.get("projectName", project_name)
    project_type = request.solution.get("solutionType", "fullstack")
    stack_id = request.solution.get("stackPreset", "custom")
    agent_ids = request.agents
    workflow_ids = request.skills + request.pipelines
    platform_id = request.platform.get("platformId", "claude-code")

    # 생성 엔진 호출 (env_vars 포함 — 엔진이 .env/.env.example 생성)
    files = generate_all(
        project_name=engine_project_name,
        project_type=project_type,
        stack_id=stack_id,
        agent_ids=agent_ids,
        workflow_ids=workflow_ids,
        platform_id=platform_id,
        env_vars=request.env_vars if request.env_vars else None,
    )

    # ZIP 패키징
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(files.items()):
            zf.writestr(path, content)

    buffer.seek(0)
    return buffer

"""Step 1 — repo clone.

App JWT → installation token → `git clone --depth=1 https://x-access-token:<tok>@github.com/<owner>/<repo>.git`.
워크스페이스는 /tmp/modernize/<session_id>/ 에 생성, Step 7 후 삭제.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from uuid import UUID

from app.services import github_app_service

_WORKSPACE_ROOT = Path("/tmp/modernize")


def workspace_path(session_id: UUID) -> Path:
    """세션별 워크스페이스 경로."""
    return _WORKSPACE_ROOT / str(session_id)


async def clone_repo(
    *,
    session_id: UUID,
    installation_id: int,
    repo_full_name: str,
    branch: str,
) -> tuple[Path, str]:
    """repo clone 수행. (워크스페이스 경로, HEAD commit SHA) 반환.

    Raises:
        RuntimeError: clone 실패 (권한/네트워크/존재하지 않는 branch 등)
    """
    if not github_app_service.is_configured():
        raise RuntimeError("GitHub App 이 설정되지 않아 clone 할 수 없습니다.")

    workspace = workspace_path(session_id)
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
    workspace.parent.mkdir(parents=True, exist_ok=True)

    token_meta = await github_app_service.get_installation_token(installation_id)
    token = token_meta.get("token")
    if not token:
        raise RuntimeError("installation token 응답에 'token' 필드 없음")

    # git clone --depth=1 — 최신 commit 만 가져옴 (분석에 충분)
    clone_url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
    cmd = [
        "git",
        "clone",
        "--depth=1",
        "--branch",
        branch,
        clone_url,
        str(workspace),
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        # token 노출 방지를 위해 stderr 에서 token 제거
        sanitized = stderr.decode("utf-8", errors="replace").replace(token, "***")
        raise RuntimeError(f"git clone 실패: {sanitized[:300]}")

    # HEAD commit SHA 조회
    head_proc = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(workspace),
        "rev-parse",
        "HEAD",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    head_out, _ = await head_proc.communicate()
    commit_sha = head_out.decode("utf-8", errors="replace").strip()

    return workspace, commit_sha


def cleanup_workspace(session_id: UUID) -> None:
    """워크스페이스 디렉토리 삭제 (Step 7)."""
    workspace = workspace_path(session_id)
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)

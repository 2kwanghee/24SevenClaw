"""프리뷰 서비스 — 위저드 설정 기반 파일 프리뷰 생성."""

from typing import Any

from app.engine.generator import generate_all
from app.schemas.preview import FileTreeNode, PreviewRequest, PreviewResponse


def _build_file_tree(file_paths: list[str]) -> list[FileTreeNode]:
    """파일 경로 목록에서 트리 구조를 생성."""
    # 디렉토리별 자식 수집
    tree_map: dict[str, dict[str, Any]] = {}

    for path in sorted(file_paths):
        parts = path.split("/")
        for i in range(len(parts)):
            current = "/".join(parts[: i + 1])
            is_file = i == len(parts) - 1
            if current not in tree_map:
                tree_map[current] = {
                    "path": current,
                    "type": "file" if is_file else "directory",
                    "children": [],
                }
            # 디렉토리 자식에 추가
            if i > 0:
                parent = "/".join(parts[:i])
                if parent in tree_map:
                    children = tree_map[parent]["children"]
                    if current not in children:
                        children.append(current)

    # 루트 노드 찾기 (부모가 없는 노드)
    all_children: set[str] = set()
    for info in tree_map.values():
        all_children.update(info["children"])

    root_paths = [p for p in tree_map if p not in all_children]

    def _build_node(path: str) -> FileTreeNode:
        info = tree_map[path]
        children = [_build_node(c) for c in sorted(info["children"])]
        return FileTreeNode(path=info["path"], type=info["type"], children=children)

    return [_build_node(p) for p in sorted(root_paths)]


def generate_preview(request: PreviewRequest) -> PreviewResponse:
    """위저드 설정 기반 프리뷰 생성."""
    # 위저드 데이터에서 생성 엔진 파라미터 추출
    project_name = request.solution.get("projectName", "my-project")
    project_type = request.solution.get("solutionType", "fullstack")
    stack_id = request.solution.get("stackPreset", "custom")
    agent_ids = request.agents
    workflow_ids = request.skills + request.pipelines
    platform_id = request.platform.get("platformId", "claude-code")

    # 생성 엔진 호출
    files = generate_all(
        project_name=project_name,
        project_type=project_type,
        stack_id=stack_id,
        agent_ids=agent_ids,
        workflow_ids=workflow_ids,
        platform_id=platform_id,
    )

    # 파일 트리 구축
    file_tree = _build_file_tree(list(files.keys()))

    return PreviewResponse(file_tree=file_tree, files=files)

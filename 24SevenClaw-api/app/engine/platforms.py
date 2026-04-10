"""플랫폼별 디렉토리 매핑 정의."""

from typing import TypedDict


class PlatformDirs(TypedDict):
    config_dir: str
    agent_dir: str
    settings_file: str
    root_guide: str


PLATFORM_DIR_MAP: dict[str, PlatformDirs] = {
    "claude-code": {
        "config_dir": ".claude",
        "agent_dir": ".claude/agents",
        "settings_file": ".claude/settings.json",
        "root_guide": "CLAUDE.md",
    },
    "gemini-cli": {
        "config_dir": ".gemini",
        "agent_dir": ".gemini/agents",
        "settings_file": ".gemini/settings.json",
        "root_guide": "GEMINI.md",
    },
    "cursor": {
        "config_dir": ".cursor",
        "agent_dir": ".cursor/rules",
        "settings_file": ".cursor/settings.json",
        "root_guide": ".cursorrules",
    },
    "codex": {
        "config_dir": ".codex",
        "agent_dir": ".codex/agents",
        "settings_file": ".codex/settings.json",
        "root_guide": "CODEX.md",
    },
}


def get_platform_dirs(platform_id: str) -> PlatformDirs:
    """플랫폼 ID에 해당하는 디렉토리 매핑 반환."""
    return PLATFORM_DIR_MAP.get(platform_id, PLATFORM_DIR_MAP["claude-code"])

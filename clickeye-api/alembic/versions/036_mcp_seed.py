"""mcp_servers 테이블에 핵심 MCP 서버 시드 데이터를 추가한다.

Revision ID: 036
Revises: 035
Create Date: 2026-05-14
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "036"
down_revision: str | None = "035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NOW = datetime.now(UTC)

_MCP_SEEDS = [
    {
        "slug": "linear",
        "name": "Linear MCP",
        "description": "Linear 이슈 트래커 연동 — 이슈 생성/조회/업데이트, 프로젝트 관리",
        "category": "project-management",
        "is_public": True,
        "body_md": (
            "# Linear MCP\n\n"
            "Linear 이슈 트래커와 Claude Code를 연동합니다.\n\n"
            "## 기능\n"
            "- 이슈 생성·조회·업데이트\n"
            "- 프로젝트 및 팀 관리\n"
            "- 싸이클/마일스톤 추적\n\n"
            "## 환경변수\n"
            "```\nLINEAR_API_KEY=lin_api_...\n```\n"
        ),
    },
    {
        "slug": "notion",
        "name": "Notion MCP",
        "description": "Notion 워크스페이스 연동 — 페이지 생성/조회, 데이터베이스 쿼리",
        "category": "knowledge-base",
        "is_public": True,
        "body_md": (
            "# Notion MCP\n\n"
            "Notion 워크스페이스와 Claude Code를 연동합니다.\n\n"
            "## 기능\n"
            "- 페이지 생성·조회·업데이트\n"
            "- 데이터베이스 쿼리 및 레코드 관리\n"
            "- 코멘트 추가\n\n"
            "## 환경변수\n"
            "```\nNOTION_API_KEY=secret_...\n```\n"
        ),
    },
    {
        "slug": "github",
        "name": "GitHub MCP",
        "description": "GitHub 저장소 연동 — PR/이슈 관리, 코드 리뷰, 브랜치 관리",
        "category": "vcs",
        "is_public": True,
        "body_md": (
            "# GitHub MCP\n\n"
            "GitHub 저장소와 Claude Code를 연동합니다.\n\n"
            "## 기능\n"
            "- PR 생성·조회·리뷰\n"
            "- 이슈 관리\n"
            "- 저장소 브랜치 관리\n\n"
            "## 환경변수\n"
            "```\nGITHUB_TOKEN=ghp_...\n```\n"
        ),
    },
    {
        "slug": "slack",
        "name": "Slack MCP",
        "description": "Slack 워크스페이스 연동 — 채널 메시지 발송, 알림, 검색",
        "category": "notification",
        "is_public": True,
        "body_md": (
            "# Slack MCP\n\n"
            "Slack 워크스페이스와 Claude Code를 연동합니다.\n\n"
            "## 기능\n"
            "- 채널·DM 메시지 발송\n"
            "- 파일 업로드\n"
            "- 메시지 검색\n\n"
            "## 환경변수\n"
            "```\nSLACK_BOT_TOKEN=xoxb-...\n```\n"
        ),
    },
    {
        "slug": "figma",
        "name": "Figma MCP",
        "description": "Figma 디자인 파일 연동 — 컴포넌트 조회, 디자인 토큰 추출, 화면 내보내기",
        "category": "design",
        "is_public": True,
        "body_md": (
            "# Figma MCP\n\n"
            "Figma 디자인 파일과 Claude Code를 연동합니다.\n\n"
            "## 기능\n"
            "- 컴포넌트·스타일 조회\n"
            "- 디자인 토큰 추출\n"
            "- 화면 PNG/SVG 내보내기\n\n"
            "## 환경변수\n"
            "```\nFIGMA_ACCESS_TOKEN=figd_...\n```\n"
        ),
    },
    {
        "slug": "jira",
        "name": "Jira MCP",
        "description": "Jira 프로젝트 관리 연동 — 이슈 CRUD, 스프린트 관리, 보드 조회",
        "category": "project-management",
        "is_public": True,
        "body_md": (
            "# Jira MCP\n\n"
            "Atlassian Jira와 Claude Code를 연동합니다.\n\n"
            "## 기능\n"
            "- 이슈 생성·조회·업데이트\n"
            "- 스프린트 관리\n"
            "- 보드·에픽 조회\n\n"
            "## 환경변수\n"
            "```\nJIRA_API_TOKEN=...\nJIRA_EMAIL=...\nJIRA_BASE_URL=https://yourcompany.atlassian.net\n```\n"
        ),
    },
    {
        "slug": "postgres",
        "name": "PostgreSQL MCP",
        "description": "PostgreSQL 데이터베이스 직접 쿼리 — 스키마 탐색, 쿼리 실행, 데이터 분석",
        "category": "database",
        "is_public": True,
        "body_md": (
            "# PostgreSQL MCP\n\n"
            "PostgreSQL 데이터베이스와 Claude Code를 연동합니다.\n\n"
            "## 기능\n"
            "- 스키마 탐색\n"
            "- SELECT/INSERT/UPDATE 실행\n"
            "- 데이터 분석 쿼리\n\n"
            "## 환경변수\n"
            "```\nDATABASE_URL=postgresql://user:pass@host:5432/db\n```\n"
        ),
    },
    {
        "slug": "telegram",
        "name": "Telegram MCP",
        "description": "Telegram 봇 연동 — 메시지 발송, 알림, 채널 관리",
        "category": "notification",
        "is_public": True,
        "body_md": (
            "# Telegram MCP\n\n"
            "Telegram 봇과 Claude Code를 연동합니다.\n\n"
            "## 기능\n"
            "- 메시지 발송·편집\n"
            "- 파일 첨부 발송\n"
            "- 그룹/채널 알림\n\n"
            "## 환경변수\n"
            "```\nTELEGRAM_BOT_TOKEN=...\n```\n"
        ),
    },
]


def upgrade() -> None:
    conn = op.get_bind()

    for item in _MCP_SEEDS:
        # 이미 존재하면 건너뜀 (idempotent)
        existing = conn.execute(
            sa.text("SELECT id FROM mcp_servers WHERE slug = :slug"),
            {"slug": item["slug"]},
        ).fetchone()
        if existing:
            continue

        conn.execute(
            sa.text(
                """
                INSERT INTO mcp_servers
                  (id, name, slug, description, body_md, version,
                   category, is_public, config_schema, created_at, updated_at)
                VALUES
                  (:id, :name, :slug, :description, :body_md, :version,
                   :category, :is_public, :config_schema, :created_at, :updated_at)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "name": item["name"],
                "slug": item["slug"],
                "description": item.get("description"),
                "body_md": item.get("body_md"),
                "version": "0.1.0",
                "category": item.get("category"),
                "is_public": item.get("is_public", True),
                "config_schema": "{}",
                "created_at": _NOW,
                "updated_at": _NOW,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    slugs = [item["slug"] for item in _MCP_SEEDS]
    conn.execute(
        sa.text("DELETE FROM mcp_servers WHERE slug = ANY(:slugs)"),
        {"slugs": slugs},
    )

#!/usr/bin/env python3
"""domain_profile_merge 단위 테스트 — 추출·신규 append·키 교체·부재 no-op."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import domain_profile_merge as dpm  # noqa: E402

REFINED_A = """# 구현 스펙

## 요약
결제 웹훅 처리기.

## 도메인 제약 (Domain Constraints)
- 데이터 민감도: 결제 카드번호는 PII — 로그 금지
- 정합성 규칙: 웹훅은 멱등 처리(중복 이벤트 무시)

## 구현 단계
1. 엔드포인트 추가
"""

REFINED_B = """# 구현 스펙

## 도메인 제약 (Domain Constraints)
- 금지 사항: 사용자 비밀번호를 평문 저장하지 않는다
"""

REFINED_A2 = """## 도메인 제약 (Domain Constraints)
- 데이터 민감도: 결제 카드번호는 PII — 토큰화 필수(갱신)
"""

REFINED_NONE = """# 구현 스펙

## 요약
단순 UI 버튼 색상 변경.

## 구현 단계
1. CSS 수정
"""


def _run(tmp_path, refined_text, ticket):
    refined = tmp_path / f"refined_{ticket}.md"
    refined.write_text(refined_text, encoding="utf-8")
    out = dpm.main(["--refined", str(refined), "--target", str(tmp_path), "--ticket", ticket])
    assert out == 0
    return tmp_path / ".claude" / "CLAUDE.domain.md"


# ── ① 섹션 추출 + 신규 파일 생성 ─────────────────────────────────────────────


def test_extract_and_create(tmp_path, capsys):
    domain = _run(tmp_path, REFINED_A, "CE-101")
    result = json.loads(capsys.readouterr().out.strip())
    assert result["merged"] is True
    assert result["ticket"] == "CE-101"

    content = domain.read_text(encoding="utf-8")
    assert dpm.FILE_HEADER in content
    assert "<!-- domain:CE-101 begin -->" in content
    assert "<!-- domain:CE-101 end -->" in content
    assert "결제 카드번호는 PII" in content
    # 도메인 섹션 헤더는 블록 안에 포함, 다음 섹션(구현 단계)은 미포함
    assert "## 도메인 제약" in content
    assert "엔드포인트 추가" not in content


# ── ② 기존 파일에 다른 키 append ─────────────────────────────────────────────


def test_append_different_key(tmp_path, capsys):
    _run(tmp_path, REFINED_A, "CE-101")
    capsys.readouterr()
    domain = _run(tmp_path, REFINED_B, "CE-102")
    result = json.loads(capsys.readouterr().out.strip())
    assert result["merged"] is True

    content = domain.read_text(encoding="utf-8")
    assert content.count(dpm.FILE_HEADER) == 1
    assert "<!-- domain:CE-101 begin -->" in content
    assert "<!-- domain:CE-102 begin -->" in content
    assert "비밀번호를 평문 저장" in content
    # 두 블록 공존
    assert content.count("begin -->") == 2


# ── ③ 같은 키 재실행 → 블록 교체(중복 없음) ─────────────────────────────────


def test_replace_same_key(tmp_path, capsys):
    _run(tmp_path, REFINED_A, "CE-101")
    capsys.readouterr()
    domain = _run(tmp_path, REFINED_A2, "CE-101")
    result = json.loads(capsys.readouterr().out.strip())
    assert result["merged"] is True

    content = domain.read_text(encoding="utf-8")
    # CE-101 블록은 정확히 하나
    assert content.count("<!-- domain:CE-101 begin -->") == 1
    assert content.count("<!-- domain:CE-101 end -->") == 1
    # 갱신된 내용으로 교체됨, 구 내용 제거
    assert "토큰화 필수(갱신)" in content
    assert "로그 금지" not in content


# ── ④ 섹션 부재 → no-op(파일 미생성) ────────────────────────────────────────


def test_no_section_noop(tmp_path, capsys):
    refined = tmp_path / "refined_none.md"
    refined.write_text(REFINED_NONE, encoding="utf-8")
    out = dpm.main(["--refined", str(refined), "--target", str(tmp_path), "--ticket", "CE-103"])
    assert out == 0
    result = json.loads(capsys.readouterr().out.strip())
    assert result["merged"] is False
    assert result["reason"] == "no_section"
    # 파일이 생성되지 않아야 한다
    assert not (tmp_path / ".claude" / "CLAUDE.domain.md").exists()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

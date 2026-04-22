"""가이드 PPTX 생성기 — python-pptx 기반 설치/실행 가이드 슬라이드 생성."""

import io

from pptx import Presentation  # type: ignore[import-untyped]
from pptx.dml.color import RGBColor  # type: ignore[import-untyped]
from pptx.enum.text import PP_ALIGN  # type: ignore[import-untyped]
from pptx.util import Inches, Pt  # type: ignore[import-untyped]

_BG = RGBColor(0x10, 0x18, 0x1A)
_ACCENT = RGBColor(0x10, 0xB9, 0x81)
_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_GRAY = RGBColor(0x94, 0xA3, 0xB8)


def _set_bg(slide: object) -> None:
    fill = slide.background.fill  # type: ignore[attr-defined]
    fill.solid()
    fill.fore_color.rgb = _BG


def _add_text(
    slide: object,
    text: str,
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    bold: bool = False,
    size: int = 16,
    color: RGBColor | None = None,
    align: object = PP_ALIGN.LEFT,
) -> None:
    tx_box = slide.shapes.add_textbox(left, top, width, height)  # type: ignore[attr-defined]
    tf = tx_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.bold = bold
    run.font.size = Pt(size)
    run.font.color.rgb = color if color is not None else _WHITE


def build_setup_guide_pptx(
    project_name: str,
    pm_slug: str,
    has_linear: bool,
    platform: str,
) -> bytes:
    """설치/실행 가이드 PPTX를 생성하여 bytes로 반환."""
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    slide_w = Inches(10)
    body_w = Inches(8.5)

    # ── 슬라이드 1: 표지 ──────────────────────────────────────────────────────
    s = prs.slides.add_slide(blank)
    _set_bg(s)
    _add_text(s, "ClickEye", Inches(0.8), Inches(1.0), slide_w, Inches(0.7),
              bold=True, size=13, color=_ACCENT)
    _add_text(s, project_name, Inches(0.8), Inches(1.9), slide_w, Inches(1.4),
              bold=True, size=34, color=_WHITE)
    _add_text(s, "설치 및 실행 가이드", Inches(0.8), Inches(3.3), slide_w, Inches(0.7),
              size=20, color=_GRAY)
    _add_text(s, f"플랫폼: {platform}", Inches(0.8), Inches(4.2), slide_w, Inches(0.6),
              size=14, color=_GRAY)

    # ── 슬라이드 2: 다운로드 & 압축 해제 ─────────────────────────────────────
    s = prs.slides.add_slide(blank)
    _set_bg(s)
    _add_text(s, "Step 1 — 다운로드 & 압축 해제",
              Inches(0.8), Inches(0.5), slide_w, Inches(0.8),
              bold=True, size=22, color=_ACCENT)
    items = [
        f"① 프로젝트 대시보드에서  {project_name}.zip  다운로드",
        "② 원하는 경로에 압축 해제",
        f"    예시: ~/projects/{project_name}/",
        "③ 터미널에서 해당 디렉토리로 이동",
    ]
    for i, line in enumerate(items):
        c = _GRAY if line.startswith("    ") else _WHITE
        _add_text(s, line, Inches(0.8), Inches(1.5 + i * 1.0), body_w, Inches(0.85),
                  size=16, color=c)

    # ── 슬라이드 3: .env 설정 ─────────────────────────────────────────────────
    s = prs.slides.add_slide(blank)
    _set_bg(s)
    _add_text(s, "Step 2 — .env API 키 설정",
              Inches(0.8), Inches(0.5), slide_w, Inches(0.8),
              bold=True, size=22, color=_ACCENT)
    _add_text(s, "프로젝트 루트의 .env 파일에 아래 키를 입력하세요",
              Inches(0.8), Inches(1.35), body_w, Inches(0.6), size=15, color=_GRAY)
    env_keys = ["ANTHROPIC_API_KEY=sk-ant-..."]
    if has_linear:
        env_keys += ["LINEAR_API_KEY=lin_api_...", "LINEAR_TEAM_ID=<team-id>"]
    for i, kv in enumerate(env_keys):
        _add_text(s, kv, Inches(0.8), Inches(2.0 + i * 0.75), Inches(7), Inches(0.65),
                  bold=True, size=14, color=_ACCENT)
    tip_y = 2.0 + len(env_keys) * 0.75 + 0.3
    _add_text(s, "📁  docs/api-keys/ 폴더에서 각 키 발급 방법을 확인하세요.",
              Inches(0.8), Inches(tip_y), body_w, Inches(0.65), size=14, color=_GRAY)

    # ── 슬라이드 4: claude + /ClickEyeStart ──────────────────────────────────
    s = prs.slides.add_slide(blank)
    _set_bg(s)
    _add_text(s, "Step 3 — Claude Code 실행 & 시작 명령",
              Inches(0.8), Inches(0.5), slide_w, Inches(0.8),
              bold=True, size=22, color=_ACCENT)
    flow = [
        ("① 터미널에서 입력:", "claude"),
        ("② Claude Code 프롬프트에서 입력:", "/ClickEyeStart"),
        ("③ .env 검증 → 누락 키를 대화형으로 안내", None),
        ("④ 셋업 완료 → AI 개발 준비 완료!", None),
    ]
    y = 1.5
    for label, cmd in flow:
        _add_text(s, label, Inches(0.8), Inches(y), body_w, Inches(0.6), size=15, color=_WHITE)
        if cmd:
            _add_text(s, cmd, Inches(1.3), Inches(y + 0.6), Inches(5), Inches(0.6),
                      bold=True, size=18, color=_ACCENT)
            y += 1.4
        else:
            y += 0.85

    # ── 슬라이드 5: Linear 연동 (조건부) ─────────────────────────────────────
    if has_linear:
        s = prs.slides.add_slide(blank)
        _set_bg(s)
        _add_text(s, "Linear 연동 설정",
                  Inches(0.8), Inches(0.5), slide_w, Inches(0.8),
                  bold=True, size=22, color=_ACCENT)
        linear_steps = [
            "① Linear API 키 발급 → .env 파일에 입력",
            "② LINEAR_TEAM_ID 설정",
            "③ /ClickEyeStart → Linear 연동 상태 자동 확인",
            "④ Webhook URL 발급 → Linear 프로젝트에 등록",
            "⑤ 이슈 생성 → Claude가 자동으로 브랜치 생성 & 개발 시작",
        ]
        for i, step in enumerate(linear_steps):
            _add_text(s, step, Inches(0.8), Inches(1.5 + i * 1.0), body_w, Inches(0.85),
                      size=15, color=_WHITE)

    # ── 슬라이드 6: 참고 문서 & 다음 단계 ───────────────────────────────────
    s = prs.slides.add_slide(blank)
    _set_bg(s)
    _add_text(s, "참고 문서 & 다음 단계",
              Inches(0.8), Inches(0.5), slide_w, Inches(0.8),
              bold=True, size=22, color=_ACCENT)
    refs = [
        ("docs/api-keys/", "각 API 키 발급 상세 가이드"),
        ("docs/WEBHOOK_SETUP.md", "Webhook 서버 설정 (Linear 연동)"),
        ("프로젝트 대시보드", "설정 변경 / ZIP 재다운로드"),
    ]
    for i, (path, desc) in enumerate(refs):
        _add_text(s, f"📄  {path}", Inches(0.8), Inches(1.5 + i * 1.1), Inches(3.5), Inches(0.6),
                  bold=True, size=14, color=_ACCENT)
        _add_text(s, desc, Inches(4.5), Inches(1.5 + i * 1.1), Inches(4.5), Inches(0.6),
                  size=14, color=_GRAY)
    _add_text(s, "문의 / 피드백: 대시보드 내 Contact 페이지",
              Inches(0.8), Inches(5.8), body_w, Inches(0.6), size=13, color=_GRAY)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()

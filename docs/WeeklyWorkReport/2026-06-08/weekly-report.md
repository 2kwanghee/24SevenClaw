제목: 6월 둘째주 주간보고

## ClickEye

1. 메타프롬프트 관측형 사전 정제를 파이프라인 기획 단계로 도입 (2026-06-11)
- metaprompt 스킬 신규 추가 (.claude/skills/metaprompt/SKILL.md)
- auto_dev_pipeline.sh STEP A: Gemini 기획을 Claude 메타프롬프트 정제로 대체 (멱등성·failsafe·Linear 코멘트·구현 프롬프트 prepend)

2. linear 스킬 선택 시 이슈 기반 개발 게이트 emit (2026-06-11)
- generator.py: linear 선택 시 clickeye-linear-gate.sh(PreToolUse hook) 등록
- 게이트 통과 조건: 부트키핑 파일 / 담당자 잠금 해제 / 활성 Linear 이슈 세션

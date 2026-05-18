"""Modernize 파이프라인 서비스 패키지 (MVP-2-A).

- `repo_service`: GitHub App installation 의 repo 목록 조회 + DB 캐시 (24h TTL)
- `clone_service` (M5): repo clone 워크스페이스 관리
- `analysis_service` (M5): scan/manifest/outdated/LLM 요약 7-step pipeline
"""

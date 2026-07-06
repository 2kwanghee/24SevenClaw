"""Modernize ZIP 에 그대로 복사되는 실행 스크립트 템플릿 모음.

이 패키지의 파일들은 두 가지 역할을 겸한다:
  1. `zip_builder.py` 가 바이트 그대로 읽어 ZIP 의 `scripts/` 에 기록하는 원본
  2. pytest 가 `import` 하여 orchestrator 로직을 단위 테스트하는 대상

customer 로컬 환경(Python 3.10+)에서 stdlib 만으로 동작해야 하므로 외부 의존성을
추가하지 않는다.
"""

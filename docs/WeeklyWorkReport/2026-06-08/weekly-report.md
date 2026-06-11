제목: 6월 둘째주 주간보고

[금주업무]

# InfraEye
1. SMS Server (완료)
- 임계치 중복 이벤트 수정(완료)
- 제거된 에이전트 정책 조회 차단(완료)
- 파일 모니터링 이벤트 발생에 대한 판정 구조 변경(완료)
- GetDBInfo 응답에 agent_id 포함 및 응답 생성 로직 반영(완료)
- SMS 구축 지원(진행중)

2. 서버시스템 FullTest (전체완료)
- 파일 정책 검증 로직 및 SMS API 개선
- 파일 정책 검증 로직 강화: 정책 필수값(경로, 정책명) 및 파일명/패턴 검증 추가
- 각 검증 단계에서 시각적 피드백 및 경고문 메시지 개선
- SMS API의 `getLogPolicyDetailTotalCount` 및 총 개수 조회 방식 수정
- 템플릿 매핑 시 트랜잭션 처리 및 기존 매핑 제거 로그 추가
- XML 매퍼 코드에서 COUNT 쿼리 및 필터 조건 로직 리팩터링
- 서비스 로직 내 사용여부(`IS_USED`) 처리 및 변환 로직 추가

# hawkeye AI
1. 모델 선정 및 평가 (완료)
- HawkEye 실제 운영 시나리오(총 30건 * 6개 유형)에 대한 3개 모델 한국어 요약 품질 비교(Phi-3/Phi-4/qwen2.5:3b)
- EC2 인프라에 따른 CPU 추론 실측(Phi-3.5 / Qwen2.5-1.5B / Qwen2.5-3B)

2. 시나리오별 프롬프트 분기 구현 (완료)
- MIRE ATT&CK / 규정 위반 / 정비창 중 발생 / 자동해소 시나리오로 각 300개 데이터 생성(openAI)

3. Phase1.5의 라우터 모델 구현 계획 수립 (완료)

4. EC2 인스턴스 유형 변경(g4dn.xlarge) 후 30개 시나리오 풀스택 테스트 (진행중)

# ClickEye
1. weekly-report 스킬 추가 — git 커밋 기반 주간보고 생성 (2026-06-11)
- collect_week.sh: 주차·제목·출력경로·커밋을 결정론적으로 수집 (`--week-offset N`으로 지난 주 지원)
- 금주(월~오늘) 커밋 수집 → 큐레이션 → `docs/WeeklyWorkReport/<주월요일>/weekly-report.md` 자동 작성

2. 메타프롬프트 관측형 사전 정제를 파이프라인 기획 단계로 도입 (2026-06-11)
- metaprompt 스킬 신규 추가 (`.claude/skills/metaprompt/SKILL.md`)
- auto_dev_pipeline.sh STEP A: Gemini 기획을 Claude 메타프롬프트 정제로 대체 (멱등성·failsafe·Linear 코멘트·구현 프롬프트 prepend)

3. linear 스킬 선택 시 이슈 기반 개발 게이트 emit (2026-06-11)
- generator.py: linear 선택 시 clickeye-linear-gate.sh(PreToolUse hook) + clickeye-gate.sh(잠금 토글) emit
- 게이트 통과 조건: 부트키핑 파일 / 담당자 잠금 해제 / 활성 Linear 이슈 세션

[차주 계획]

# hawkeye
1. 라우터 모델 프롬프트 개발
2. 상관관계 서술 / 이상 설명 테스트
3. 라우터 모델 붙여서 시나리오 실행
4. 코드 정리 및 로컬 온보딩 세팅

# ClickEye
1. 인도네시아 언어팩 준비

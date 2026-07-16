# Temporal 오케스트레이션 패키지 (CE-296, P0 토대)
#
# 스트랭글러 패턴: 기존 auto_dev_pipeline.sh 옆에 Temporal 레일을 세운다.
# 이 패키지는 `feature_temporal` 토글이 켜졌을 때만 실동작한다(기본 off → 회귀 0).
# 현 단계는 워커 스켈레톤 + 빈 워크플로 1개만 제공하며, 실 워크플로 글루는 P1에서 추가한다.

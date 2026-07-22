"""운영(Ops) 패널 서비스 — superadmin 전용 읽기 전용 인프라 조회.

Docker 상태/포트 상태 조회는 read-only 소켓 프록시(dockerproxy, GET 전용)와
TCP 프로브만 사용한다. 어떤 컴포넌트도 docker 소켓을 raw 로 쥐지 않으며,
inspect 응답에서 환경변수(Config.Env)/명령(Config.Cmd)은 무조건 스트립한다.
"""

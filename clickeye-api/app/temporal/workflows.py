"""Temporal 워크플로 정의 (CE-296 스켈레톤).

현 단계는 헬스체크용 빈 워크플로 1개만 둔다. 실제 SI 딜리버리 워크플로
(auto_dev_pipeline 이주분)는 P1에서 이 모듈에 추가한다.
"""

from temporalio import workflow


@workflow.defn
class HealthCheckWorkflow:
    """워커 기동·연결 검증용 최소 워크플로.

    입력 이름을 받아 확인 문자열을 반환한다. 부작용(activity 호출 등)이 없어
    Temporal 서버가 스케줄링 경로만 검증하면 되는 스모크 테스트에 쓴다.
    """

    @workflow.run
    async def run(self, name: str = "clickeye") -> str:
        return f"clickeye-temporal-ok: {name}"

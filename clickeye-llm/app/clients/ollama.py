"""Ollama 비동기 클라이언트 — 임베딩 + 생성.

★스위처블 원칙★: 모델명은 전부 config(embed_model/llm_model)에서 주입한다.
하드코딩 금지 — env 만 바꾸면 백엔드 모델 교체(회귀 0).
"""

from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger("clickeye-llm.ollama")


class OllamaError(RuntimeError):
    """Ollama 호출 실패(네트워크/HTTP/응답형식)를 감싸는 예외."""


class OllamaClient:
    """호스트에서 도는 Ollama 를 참조하는 얇은 async 클라이언트.

    - embed(texts): /api/embed(배치) 로 임베딩 벡터 리스트 반환.
    - generate(prompt, system): /api/generate(stream=false) 로 완성 텍스트 반환.
    """

    def __init__(
        self,
        base_url: str,
        embed_model: str,
        llm_model: str,
        timeout: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._embed_model = embed_model
        self._llm_model = llm_model
        # 외부 주입(테스트) 없으면 자체 생성. own=True 면 close 책임을 가진다.
        self._own_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        if self._own_client:
            await self._client.aclose()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """텍스트 목록 → 임베딩 벡터 목록.

        신형 /api/embed(input=배치) 우선, 미지원 시 /api/embeddings(prompt=단건) 폴백.
        """
        if not texts:
            return []
        url = f"{self._base_url}/api/embed"
        try:
            resp = await self._client.post(
                url, json={"model": self._embed_model, "input": texts}
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings")
            if embeddings:
                return [list(map(float, v)) for v in embeddings]
            # 일부 구형 응답은 단일 embedding 키만 준다.
            single = data.get("embedding")
            if single is not None and len(texts) == 1:
                return [list(map(float, single))]
            raise OllamaError(f"임베딩 응답에 embeddings 키 없음: keys={list(data.keys())}")
        except httpx.HTTPStatusError as exc:
            # /api/embed 미지원(404 등) 시 레거시 엔드포인트로 폴백.
            if exc.response.status_code == 404:
                logger.warning("/api/embed 미지원 → /api/embeddings 폴백")
                return await self._embed_legacy(texts)
            raise OllamaError(f"임베딩 HTTP 오류: {exc}") from exc
        except httpx.HTTPError as exc:
            raise OllamaError(f"임베딩 요청 실패: {exc}") from exc

    async def _embed_legacy(self, texts: list[str]) -> list[list[float]]:
        """/api/embeddings 는 단건(prompt) 이므로 순차 호출로 배치를 구성."""
        url = f"{self._base_url}/api/embeddings"
        out: list[list[float]] = []
        for text in texts:
            resp = await self._client.post(
                url, json={"model": self._embed_model, "prompt": text}
            )
            resp.raise_for_status()
            emb = resp.json().get("embedding")
            if emb is None:
                raise OllamaError("레거시 임베딩 응답에 embedding 키 없음")
            out.append(list(map(float, emb)))
        return out

    async def generate(self, prompt: str, system: str | None = None) -> str:
        """단발 생성(stream=false). 완성 텍스트만 반환."""
        url = f"{self._base_url}/api/generate"
        payload: dict[str, object] = {
            "model": self._llm_model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        try:
            resp = await self._client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            response = data.get("response")
            if response is None:
                raise OllamaError(f"생성 응답에 response 키 없음: keys={list(data.keys())}")
            return str(response).strip()
        except httpx.HTTPError as exc:
            raise OllamaError(f"생성 요청 실패: {exc}") from exc

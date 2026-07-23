"""인테이크 수주 서비스 — Chunk A1 + A3-lite.

외부 서비스 키 인증(sha256), 3형태(structured/document/url) 수신·정규화, 멱등 처리,
게이트 전이(accept → Project 생성 + KB 인제스트 훅 / reject)를 담당한다.

A3-lite 추가:
- url fetch SSRF 하드닝 — fetch/리다이렉트 전 호스트를 DNS 해석해 사설·루프백·
  링크로컬·예약·멀티캐스트 대역 및 클라우드 메타데이터 IP(169.254.169.254)를 차단.
- callback 상태 푸시 — accept/reject 시 callback_url 로 서명된 상태 통지 POST
  (fire-and-forget, llm_ingest 패턴).

CE-311 하드닝:
- SSRF 커넥션 IP 고정(TOCTOU/DNS 재바인딩 방어) — 검증을 통과한 IP 로 URL 호스트를
  치환해 연결하고, Host 헤더·SNI(https, httpx `sni_hostname` extension)는 원 호스트를
  유지한다. TLS 인증서 검증도 원 호스트 기준(SNI hostname)으로 수행되므로 https 도
  검증 손실 없이 고정된다. url fetch(리다이렉트 hop 포함)와 콜백 발송 양쪽 적용.
- 콜백 재시도 큐(at-least-once) — accept/reject 시 pending 기록 후 즉시 1회 시도,
  실패 시 백오프(1m→5m→30m→2h→6h)로 재시도. 총 6회(초기 1 + 재시도 5) 초과 실패 시
  failed. lifespan 워커(main.py, FEATURE_INTAKE on 일 때만)가 60s 폴링으로 due 건을
  재발송한다(HMAC 서명·SSRF 가드 동일). Temporal 이관은 후속 과제.
"""

import asyncio
import hashlib
import hmac
import html
import ipaddress
import json
import logging
import re
import secrets
import socket
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.intake import IntakeRequest, IntakeServiceKey
from app.models.project import Project
from app.models.user import User
from app.schemas.intake import IntakeCreate
from app.services.llm_ingest import enqueue_ingest

logger = logging.getLogger(__name__)

# url fetch 정책: 타임아웃 15초, 본문 상한 2MB, text/html·text/plain 만 허용.
FETCH_TIMEOUT = 15.0
FETCH_MAX_BYTES = 2 * 1024 * 1024
_ALLOWED_CONTENT_TYPES = ("text/html", "text/plain")
# 수동 리다이렉트 추적 상한 (각 hop 마다 SSRF 재검증).
MAX_REDIRECTS = 3
# callback 푸시 정책: 타임아웃 10초, fire-and-forget (llm_ingest 패턴).
CALLBACK_TIMEOUT = 10.0
# CE-311 콜백 재시도 백오프(초): 1m → 5m → 30m → 2h → 6h.
CALLBACK_BACKOFF_SECONDS: tuple[int, ...] = (60, 300, 1800, 7200, 21600)
# 총 허용 발송 시도 횟수 = 초기 1회 + 백오프 재시도 5회. 초과 실패 시 failed 확정.
CALLBACK_MAX_TOTAL_ATTEMPTS = 1 + len(CALLBACK_BACKOFF_SECONDS)
# accept/reject 트랜잭션에서 pending 기록 시의 안전망 재시도 시각(초) — 즉시 1회
# 시도의 결과 기록 자체가 유실돼도 워커가 이 시각 이후 재발송한다(at-least-once).
CALLBACK_PENDING_SAFETY_SECONDS = 60
# 클라우드 메타데이터 엔드포인트 — link-local 이지만 위험도가 높아 명시 차단.
_METADATA_IPS = frozenset({ipaddress.ip_address("169.254.169.254")})

# fire-and-forget 콜백 태스크 강한 참조(GC 조기 소멸 방지 — llm_ingest 패턴).
_callback_tasks: set[asyncio.Task[None]] = set()


class SSRFBlockedError(ValueError):
    """SSRF 가드에 걸린 URL — fetch 를 수행하지 않고 사유를 기록한다."""


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """사설/루프백/링크로컬/예약/멀티캐스트/미지정 대역 + 메타데이터 IP 여부."""
    # IPv4-mapped IPv6(::ffff:127.0.0.1 등)는 내장 IPv4 로 풀어서 검사한다.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return (
        ip in _METADATA_IPS
        or ip.is_private  # 10./172.16-31./192.168./fc00:: 등
        or ip.is_loopback  # 127./::1
        or ip.is_link_local  # 169.254./fe80::
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified  # 0.0.0.0/::
    )


async def _resolve_public_ip(url: str) -> str:
    """URL 호스트를 DNS 해석해 모든 결과 IP 가 공인 대역인지 검증하고, 검증을
    통과한 IP 하나(IPv4 우선)를 반환한다 — 반환 IP 로 커넥션을 고정한다.

    위반 시 SSRFBlockedError("SSRF_BLOCKED: ...") 를 던진다.

    DNS 재바인딩(TOCTOU) 방어: 여기서 검증한 IP 를 _pinned_request_parts 로 URL
    호스트에 치환해 연결하므로, 검증과 연결 사이에 DNS 응답이 내부망 IP 로 바뀌어도
    실제 커넥션은 검증된 IP 로만 나간다. Host 헤더·SNI 는 원 호스트를 유지한다.
    """
    parsed = httpx.URL(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFBlockedError(f"SSRF_BLOCKED: 허용되지 않는 스킴 '{parsed.scheme}'")
    host = parsed.host
    if not host:
        raise SSRFBlockedError("SSRF_BLOCKED: 호스트가 없는 URL")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(
            host, None, type=socket.SOCK_STREAM
        )
    except (socket.gaierror, OSError) as exc:
        raise SSRFBlockedError(f"SSRF_BLOCKED: 호스트 해석 실패 '{host}' ({exc})") from exc
    candidates: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        # sockaddr[0] = IP 문자열 (IPv6 scope id 는 제거 후 파싱).
        ip = ipaddress.ip_address(str(info[4][0]).split("%")[0])
        if _is_blocked_ip(ip):
            raise SSRFBlockedError(f"SSRF_BLOCKED: 비공개 대역 IP {ip} (host={host})")
        candidates.append(ip)
    if not candidates:
        raise SSRFBlockedError(f"SSRF_BLOCKED: 해석 결과 IP 없음 (host={host})")
    # IPv4 우선(이중 스택 환경 호환) — 없으면 첫 IPv6.
    for ip in candidates:
        if isinstance(ip, ipaddress.IPv4Address):
            return str(ip)
    return str(candidates[0])


def _pinned_request_parts(
    url: str, ip: str
) -> tuple[httpx.URL, dict[str, str], dict[str, Any]]:
    """검증된 IP 로 커넥션을 고정한 요청 구성요소(url, headers, extensions)를 만든다.

    - URL 호스트를 IP 로 치환 → TCP 연결이 검증된 IP 로만 나간다(재해석 없음).
    - Host 헤더는 원 호스트(:포트 포함)를 유지 → 가상호스트 라우팅 보존.
    - https 는 httpx/httpcore 의 `sni_hostname` request extension 으로 SNI 를 원
      호스트로 지정한다. Python ssl 은 인증서 hostname 검증을 server_hostname
      (= sni_hostname) 기준으로 수행하므로 TLS 검증 손실 없이 IP 고정이 성립한다.
    """
    parsed = httpx.URL(url)
    host = parsed.host
    host_header = host if parsed.port is None else f"{host}:{parsed.port}"
    pinned_url = parsed.copy_with(host=ip)
    headers = {"Host": host_header}
    extensions: dict[str, Any] = {}
    if parsed.scheme == "https":
        extensions["sni_hostname"] = host
    return pinned_url, headers, extensions


def _hash_key(raw: str) -> str:
    """평문 키 → sha256 hexdigest (project.setup_token_hash 패턴)."""
    return hashlib.sha256(raw.encode()).hexdigest()


def _slugify(text_value: str) -> str:
    """간단 slug 생성 (project_service 패턴). 한글 등으로 비면 호출부에서 폴백."""
    slug = text_value.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")


def _strip_html(raw: str) -> str:
    """간단 태그 제거 — script/style/주석 삭제 → 태그 제거 → 엔티티 복원 → 공백 정리.

    A1 범위의 초안 추출이다. LLM 기반 정제(metaprompt)는 A3 에서 고도화한다.
    """
    text_value = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
    text_value = re.sub(r"(?s)<!--.*?-->", " ", text_value)
    text_value = re.sub(r"(?s)<[^>]+>", " ", text_value)
    text_value = html.unescape(text_value)
    return re.sub(r"\s+", " ", text_value).strip()


async def _fetch_url_text(url: str) -> str:
    """url 본문을 fetch 하여 텍스트를 추출한다. 실패 시 예외를 던진다(호출부에서 흡수).

    SSRF 하드닝(A3-lite): 스킴 검증(http/https)은 IntakeCreate 에서 1차 수행하고,
    여기서 매 요청 전 호스트를 DNS 해석해 사설/루프백/링크로컬/예약/멀티캐스트
    대역과 메타데이터 IP 를 차단한다. 리다이렉트는 follow_redirects=False 로 끄고
    수동으로 최대 MAX_REDIRECTS 회 추적하며 각 Location 호스트를 재검증한다.
    본문은 스트리밍으로 FETCH_MAX_BYTES 까지만 읽는다(초과분 절단).

    CE-311 커넥션 IP 고정(DNS 재바인딩 방어): 매 hop 마다 검증을 통과한 IP 로 URL
    호스트를 치환해 연결한다(Host 헤더·SNI 는 원 호스트, _pinned_request_parts 참조).
    검증→연결 사이 DNS 재해석 창구가 사라지므로 TOCTOU 재바인딩이 차단된다.
    """
    current_url = url
    async with httpx.AsyncClient(timeout=FETCH_TIMEOUT, follow_redirects=False) as client:
        for _hop in range(MAX_REDIRECTS + 1):
            ip = await _resolve_public_ip(current_url)
            pinned_url, pin_headers, pin_extensions = _pinned_request_parts(current_url, ip)
            async with client.stream(
                "GET", pinned_url, headers=pin_headers, extensions=pin_extensions
            ) as resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("location")
                    if not location:
                        raise ValueError("리다이렉트 응답에 Location 헤더가 없습니다.")
                    current_url = str(httpx.URL(current_url).join(location))
                    continue  # 다음 루프 진입부에서 새 호스트 재검증
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                if content_type not in _ALLOWED_CONTENT_TYPES:
                    raise ValueError(f"허용되지 않는 Content-Type: {content_type or '(없음)'}")
                chunks: list[bytes] = []
                total = 0
                async for chunk in resp.aiter_bytes():
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= FETCH_MAX_BYTES:
                        break
                raw = b"".join(chunks)[:FETCH_MAX_BYTES].decode(
                    resp.charset_encoding or "utf-8", errors="replace"
                )
                if content_type == "text/html":
                    return _strip_html(raw)
                return re.sub(r"\s+", " ", raw).strip()
        raise SSRFBlockedError(f"SSRF_BLOCKED: 리다이렉트 한도({MAX_REDIRECTS}회) 초과")


def _build_callback_body(intake: IntakeRequest) -> dict:
    """콜백 페이로드 — 재시도 시에도 현재 상태 기준으로 재생성한다(timestamp 갱신)."""
    return {
        "intake_id": str(intake.id),
        "status": intake.status,
        "project_id": str(intake.project_id) if intake.project_id else None,
        "title": intake.title,
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def _send_callback(callback_url: str, secret: str, body: dict) -> None:
    """콜백 1회 발송 — 실패 시 예외를 던진다(재시도 판단은 호출부 책임).

    서명 스펙: X-ClickEye-Signature = HMAC-SHA256 hexdigest,
      key     = 해당 인테이크를 접수한 서비스 키의 key_hash 문자열
                (= sha256(발급 평문 키) hexdigest),
      message = 요청 본문 raw bytes(전송된 JSON 그대로).
    외부 서비스 검증법: 자신이 보관한 평문 서비스 키를 sha256 hexdigest 한 값을
    시크릿으로 삼아 수신 본문 bytes 의 HMAC-SHA256 을 계산, 헤더와 비교하면 된다.

    SSRF 가드(CE-311): 콜백 대상도 DNS 해석·공인 대역 검증 후 그 IP 로 커넥션을
    고정한다(Host/SNI 원 호스트 유지) — 내부망 콜백·DNS 재바인딩 차단.
    """
    ip = await _resolve_public_ip(callback_url)
    pinned_url, pin_headers, pin_extensions = _pinned_request_parts(callback_url, ip)
    raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
    signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    async with httpx.AsyncClient(timeout=CALLBACK_TIMEOUT) as client:
        resp = await client.post(
            pinned_url,
            content=raw,
            headers={
                **pin_headers,
                "Content-Type": "application/json",
                "X-ClickEye-Signature": signature,
            },
            extensions=pin_extensions,
        )
        resp.raise_for_status()


def _apply_callback_result(intake: IntakeRequest, ok: bool, error: str | None) -> None:
    """발송 시도 1회의 결과를 IntakeRequest 콜백 컬럼에 반영한다(커밋은 호출부).

    성공 → sent(재시도 종료). 실패 → attempts 증가 후 백오프 스케줄:
    1m→5m→30m→2h→6h, 총 CALLBACK_MAX_TOTAL_ATTEMPTS(6)회 초과 실패 시 failed 확정.
    """
    attempts = int(intake.callback_attempts or 0) + 1
    intake.callback_attempts = attempts  # type: ignore[assignment]
    if ok:
        intake.callback_status = "sent"  # type: ignore[assignment]
        intake.callback_next_retry_at = None  # type: ignore[assignment]
        intake.callback_last_error = None  # type: ignore[assignment]
        return
    intake.callback_last_error = (error or "")[:2000]  # type: ignore[assignment]
    if attempts >= CALLBACK_MAX_TOTAL_ATTEMPTS:
        intake.callback_status = "failed"  # type: ignore[assignment]
        intake.callback_next_retry_at = None  # type: ignore[assignment]
        return
    backoff = CALLBACK_BACKOFF_SECONDS[min(attempts - 1, len(CALLBACK_BACKOFF_SECONDS) - 1)]
    intake.callback_status = "pending"  # type: ignore[assignment]
    intake.callback_next_retry_at = datetime.now(UTC) + timedelta(  # type: ignore[assignment]
        seconds=backoff
    )


def _open_session() -> Any:
    """백그라운드 기록용 세션 컨텍스트 — 지연 import(테스트에서 대체 가능)."""
    from app.database import async_session  # noqa: PLC0415 — 앱 기동 순서/테스트 주입 대응

    return async_session()


async def _record_callback_result(intake_id: UUID, ok: bool, error: str | None) -> None:
    """fire-and-forget 발송 결과를 별도 세션으로 DB 에 기록한다. 예외 비전파.

    기록 실패 시 row 는 accept/reject 트랜잭션이 남긴 pending(+안전망 재시도 시각)
    그대로 유지되어 워커가 재발송한다 — at-least-once 는 지켜진다(중복 가능, 멱등은
    수신측 intake_id 기준 처리 권장).
    """
    try:
        async with _open_session() as db:
            intake = await db.get(IntakeRequest, intake_id)
            if intake is None or intake.callback_status not in ("pending",):
                return
            _apply_callback_result(intake, ok, error)
            await db.commit()
    except Exception as exc:  # noqa: BLE001 — 기록 실패는 원 요청에 절대 전파 금지
        logger.warning("인테이크 콜백 결과 기록 실패(무시): intake_id=%s err=%s", intake_id, exc)


async def _attempt_callback(intake_id: UUID, callback_url: str, secret: str, body: dict) -> None:
    """즉시 1회 발송 시도 코루틴 — 결과를 DB 에 기록하고 예외는 삼킨다."""
    try:
        await _send_callback(callback_url, secret, body)
        ok, error = True, None
    except Exception as exc:  # noqa: BLE001 — 콜백 실패는 재시도 큐가 흡수
        ok, error = False, f"{type(exc).__name__}: {exc}"
        logger.warning("인테이크 콜백 실패(재시도 예약): url=%s err=%s", callback_url, exc)
    await _record_callback_result(intake_id, ok, error)


def _mark_callback_pending(intake: IntakeRequest, key: IntakeServiceKey | None) -> None:
    """accept/reject 트랜잭션 안에서 콜백 발송 대기 상태를 기록한다(커밋은 호출부).

    callback_url 없음/키 없음 → none 유지. 안전망 next_retry_at(+60s)을 함께 기록해
    즉시 시도의 결과 기록이 유실돼도 워커가 재발송한다.
    """
    if not intake.callback_url or key is None:
        return
    intake.callback_status = "pending"  # type: ignore[assignment]
    intake.callback_attempts = 0  # type: ignore[assignment]
    intake.callback_next_retry_at = datetime.now(UTC) + timedelta(  # type: ignore[assignment]
        seconds=CALLBACK_PENDING_SAFETY_SECONDS
    )
    intake.callback_last_error = None  # type: ignore[assignment]


def _enqueue_callback(intake: IntakeRequest, key: IntakeServiceKey | None) -> None:
    """accept/reject 상태 콜백을 fire-and-forget 으로 예약한다. 예외 비전파.

    - callback_url 없음 / 서비스 키 조회 실패 → 조용히 no-op.
    - 이벤트 루프 없음(sync 컨텍스트) → 비차단 원칙상 스킵(warning) — pending 은
      이미 기록돼 있으므로 재시도 워커가 발송을 이어받는다.
    """
    try:
        if not intake.callback_url or key is None:
            return
        body = _build_callback_body(intake)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("이벤트 루프 없음 — 인테이크 콜백 스킵: intake_id=%s", intake.id)
            return
        task = loop.create_task(
            _attempt_callback(intake.id, str(intake.callback_url), str(key.key_hash), body)
        )
        _callback_tasks.add(task)
        task.add_done_callback(_callback_tasks.discard)
    except Exception as exc:  # noqa: BLE001 — 예약 실패도 호출자에게 전파 금지
        logger.warning("인테이크 콜백 예약 실패(무시): intake_id=%s err=%s", intake.id, exc)


async def process_due_callbacks(db: AsyncSession, limit: int = 20) -> int:
    """next_retry_at 이 도래한 pending 콜백을 재발송한다. 발송 성공 건수를 반환.

    lifespan 재시도 워커(main.py, 60s 폴링)가 호출한다 — 서명/SSRF 가드는 즉시
    발송 경로(_send_callback)와 동일하다. Temporal 이관은 후속 과제.
    """
    now = datetime.now(UTC)
    rows = (
        await db.execute(
            select(IntakeRequest)
            .where(
                IntakeRequest.callback_status == "pending",
                IntakeRequest.callback_next_retry_at.is_not(None),
                IntakeRequest.callback_next_retry_at <= now,
            )
            .order_by(IntakeRequest.callback_next_retry_at.asc())
            .limit(limit)
        )
    ).scalars().all()
    sent = 0
    for intake in rows:
        key = await db.get(IntakeServiceKey, intake.service_key_id)
        if key is None or not intake.callback_url:
            # 재시도 불가능 상태 — 즉시 failed 확정(무한 폴링 방지).
            intake.callback_status = "failed"  # type: ignore[assignment]
            intake.callback_next_retry_at = None  # type: ignore[assignment]
            intake.callback_last_error = "콜백 재시도 불가: 서비스 키/URL 없음"  # type: ignore[assignment]
            continue
        try:
            await _send_callback(
                str(intake.callback_url), str(key.key_hash), _build_callback_body(intake)
            )
            _apply_callback_result(intake, True, None)
            sent += 1
        except Exception as exc:  # noqa: BLE001 — 개별 실패는 다음 백오프로 이월
            _apply_callback_result(intake, False, f"{type(exc).__name__}: {exc}")
            logger.warning(
                "인테이크 콜백 재시도 실패: intake_id=%s attempts=%s err=%s",
                intake.id,
                intake.callback_attempts,
                exc,
            )
    await db.commit()
    return sent


class IntakeService:
    """인테이크 수주 비즈니스 로직."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 서비스 키
    # ------------------------------------------------------------------

    async def authenticate_key(self, raw_key: str | None) -> IntakeServiceKey:
        """X-ClickEye-Service-Key 평문을 sha256 비교로 검증한다. 실패 시 401."""
        if not raw_key:
            raise AppError("INTAKE_KEY_REQUIRED", "X-ClickEye-Service-Key 헤더가 필요합니다.", 401)
        result = await self.db.execute(
            select(IntakeServiceKey).where(
                IntakeServiceKey.key_hash == _hash_key(raw_key),
                IntakeServiceKey.is_active.is_(True),
            )
        )
        key = result.scalar_one_or_none()
        if key is None:
            raise AppError("INTAKE_KEY_INVALID", "유효하지 않은 서비스 키입니다.", 401)
        return key

    async def create_service_key(
        self, name: str, organization_id: UUID | None
    ) -> tuple[str, IntakeServiceKey]:
        """서비스 키 발급 — 평문은 반환값으로 1회만 노출, DB에는 해시만 저장."""
        raw = secrets.token_urlsafe(32)
        key = IntakeServiceKey(name=name, key_hash=_hash_key(raw), organization_id=organization_id)
        self.db.add(key)
        await self.db.commit()
        await self.db.refresh(key)
        return raw, key

    async def list_service_keys(self) -> list[IntakeServiceKey]:
        """전체 서비스 키 목록 (해시 미노출은 응답 스키마가 보장)."""
        result = await self.db.execute(
            select(IntakeServiceKey).order_by(IntakeServiceKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def deactivate_service_key(self, key_id: UUID) -> IntakeServiceKey:
        """서비스 키 비활성화(soft delete) — 이후 해당 키 인증은 401."""
        key = await self.db.get(IntakeServiceKey, key_id)
        if key is None:
            raise AppError("INTAKE_KEY_NOT_FOUND", "서비스 키를 찾을 수 없습니다.", 404)
        key.is_active = False  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(key)
        return key

    # ------------------------------------------------------------------
    # 수주 접수
    # ------------------------------------------------------------------

    async def create_intake(
        self,
        key: IntakeServiceKey,
        data: IntakeCreate,
        idempotency_key: str | None,
    ) -> IntakeRequest:
        """수주 접수 — 멱등 재수신 시 기존 레코드를 그대로 반환한다(202 동일)."""
        if idempotency_key:
            result = await self.db.execute(
                select(IntakeRequest).where(
                    IntakeRequest.service_key_id == key.id,
                    IntakeRequest.idempotency_key == idempotency_key,
                )
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                return existing

        payload: dict = {}
        normalized_text: str | None = None

        if data.input_type == "structured":
            payload["requirements"] = data.requirements
            # dict 를 보기 좋게 직렬화 (검토 콘솔/Project.requirements_text 용).
            normalized_text = json.dumps(data.requirements, ensure_ascii=False, indent=2)
        elif data.input_type == "document":
            assert data.document is not None  # 스키마 validator 가 보장
            payload["document"] = data.document.model_dump()
            normalized_text = data.document.content
        else:  # url
            payload["source_url"] = data.source_url
            try:
                normalized_text = await _fetch_url_text(str(data.source_url))
            except SSRFBlockedError as exc:
                # SSRF 차단 — fetch 미수행, 접수는 202 유지(비차단 계약 불변).
                normalized_text = None
                payload["fetch_error"] = str(exc)
            except Exception as exc:  # noqa: BLE001 — fetch 실패는 접수 자체를 막지 않는다
                normalized_text = None
                payload["fetch_error"] = f"{type(exc).__name__}: {exc}"

        intake = IntakeRequest(
            service_key_id=key.id,
            idempotency_key=idempotency_key,
            input_type=data.input_type,
            title=data.title,
            payload=payload,
            normalized_text=normalized_text,
            source_url=data.source_url,
            target=data.target,
            priority=data.priority,
            callback_url=data.callback_url,
            status="pending_review",
        )
        self.db.add(intake)
        await self.db.commit()
        await self.db.refresh(intake)
        return intake

    # ------------------------------------------------------------------
    # 검토/전이
    # ------------------------------------------------------------------

    async def _get_pending(self, intake_id: UUID) -> IntakeRequest:
        """pending_review 상태의 인테이크를 조회한다. 없으면 404, 상태 불일치 409."""
        intake = await self.db.get(IntakeRequest, intake_id)
        if intake is None:
            raise AppError("INTAKE_NOT_FOUND", "인테이크 요청을 찾을 수 없습니다.", 404)
        if intake.status != "pending_review":
            raise AppError(
                "INTAKE_INVALID_STATUS",
                f"pending_review 상태에서만 처리할 수 있습니다. (현재: {intake.status})",
                409,
            )
        return intake

    async def list_refine_pending(self, limit: int = 10) -> list[IntakeRequest]:
        """정제 대기 목록 — pending_review & refine_status=pending, 오래된 순(FIFO).

        로컬 정제 배치(scripts/intake_refine.sh)가 소비한다. 서버는 LLM 을 호출하지
        않는다 — 실행 플레인 분리(A3-full).
        """
        result = await self.db.execute(
            select(IntakeRequest)
            .where(
                IntakeRequest.status == "pending_review",
                IntakeRequest.refine_status == "pending",
            )
            .order_by(IntakeRequest.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def submit_refined(self, intake_id: UUID, refined_text: str) -> IntakeRequest:
        """정제 결과 저장 — 비공백이면 refined, 공백만이면 skipped(재시도 대상 제외).

        pending_review 아닌 건은 _get_pending 이 409 를 던진다(정제 무의미).
        """
        intake = await self._get_pending(intake_id)
        if refined_text.strip():
            intake.refined_text = refined_text  # type: ignore[assignment]
            intake.refine_status = "refined"  # type: ignore[assignment]
        else:
            intake.refined_text = None  # type: ignore[assignment]
            intake.refine_status = "skipped"  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(intake)
        return intake

    async def accept(self, intake_id: UUID, user: User) -> IntakeRequest:
        """승인 — Project 생성(딜리버리 등록) 후 accepted 로 전이 + KB 인제스트 훅.

        A3-full: 요구사항 텍스트는 정제 스펙(refined_text) 우선, 없으면
        normalized_text 폴백(기존 동작 유지). KB 인제스트 텍스트도 동일 우선.
        """
        intake = await self._get_pending(intake_id)
        key = await self.db.get(IntakeServiceKey, intake.service_key_id)

        requirements_source = intake.refined_text or intake.normalized_text
        slug = _slugify(str(intake.title)) or f"intake-{intake.id.hex[:8]}"
        project = Project(
            owner_id=user.id,
            name=intake.title,
            slug=slug,
            requirements_text=requirements_source,
            organization_id=key.organization_id if key is not None else None,
            project_type="intake",
        )
        self.db.add(project)
        await self.db.flush()  # project.id 확보

        intake.project_id = project.id
        intake.status = "accepted"  # type: ignore[assignment]
        # CE-311: 콜백 발송 대기 상태를 같은 트랜잭션에 기록(at-least-once 안전망).
        _mark_callback_pending(intake, key)
        await self.db.commit()
        await self.db.refresh(intake)

        # P1.5 KB 인제스트 훅 — 토글 off 면 no-op, 예외 비전파(fire-and-forget).
        enqueue_ingest(
            project.id,
            f"intake:{intake.id}",
            f"[인테이크 수주] {intake.title}\n{requirements_source or ''}",
            metadata={"kind": "intake", "input_type": intake.input_type},
        )
        # A3-lite: 외부 서비스에 승인 상태 푸시(fire-and-forget, 서명 포함).
        _enqueue_callback(intake, key)
        return intake

    async def reject(self, intake_id: UUID, user: User, reason: str | None = None) -> IntakeRequest:
        """반려 — rejected 로 전이하고 사유/처리자를 payload 에 기록한다."""
        intake = await self._get_pending(intake_id)
        # JSON 컬럼 in-place 변경은 감지되지 않으므로 새 dict 로 재할당한다.
        intake.payload = {
            **(intake.payload or {}),
            "reject_reason": reason,
            "rejected_by": str(user.id),
        }
        intake.status = "rejected"  # type: ignore[assignment]
        # CE-311: 콜백 발송 대기 상태를 같은 트랜잭션에 기록(at-least-once 안전망).
        key = await self.db.get(IntakeServiceKey, intake.service_key_id)
        _mark_callback_pending(intake, key)
        await self.db.commit()
        await self.db.refresh(intake)
        # A3-lite: 외부 서비스에 반려 상태 푸시(fire-and-forget, 서명 포함).
        _enqueue_callback(intake, key)
        return intake

    async def list_intakes(
        self, user: User, status_filter: str | None = None
    ) -> list[IntakeRequest]:
        """검토 목록 — superadmin 은 전체, admin 은 자기 조직 소속 키의 요청만."""
        stmt = select(IntakeRequest).order_by(IntakeRequest.created_at.desc())
        if status_filter:
            stmt = stmt.where(IntakeRequest.status == status_filter)
        if getattr(user, "system_role", "") != "superadmin":
            # admin 조직 스코프: 자기 조직 키가 접수한 요청만. 무조직 admin 은 빈 목록.
            stmt = stmt.join(
                IntakeServiceKey, IntakeRequest.service_key_id == IntakeServiceKey.id
            ).where(IntakeServiceKey.organization_id == user.organization_id)
            if user.organization_id is None:
                return []
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

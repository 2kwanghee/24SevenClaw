"""에러 코드별 i18n 메시지 레지스트리.

기존 호출처는 그대로 두되, 새 발생 케이스부터 from_key()로 opt-in한다.
admin 전용 엔드포인트는 항상 ko 메시지를 사용한다.
"""

from __future__ import annotations

_MESSAGES: dict[str, dict[str, str]] = {
    "LANGUAGE_INVALID": {
        "ko": "지원하지 않는 언어 코드입니다. 'ko' 또는 'en'만 허용됩니다.",
        "en": "Unsupported language code. Only 'ko' and 'en' are allowed.",
    },
    "USER_NOT_FOUND": {
        "ko": "사용자를 찾을 수 없습니다.",
        "en": "User not found.",
    },
    "EMAIL_EXISTS": {
        "ko": "이미 등록된 이메일입니다.",
        "en": "Email address is already registered.",
    },
    "INVALID_CREDENTIALS": {
        "ko": "이메일 또는 비밀번호가 올바르지 않습니다.",
        "en": "Invalid email or password.",
    },
    "USER_INACTIVE": {
        "ko": "비활성화된 계정입니다.",
        "en": "Account is deactivated.",
    },
    "INVALID_TOKEN": {
        "ko": "유효하지 않은 토큰입니다.",
        "en": "Invalid token.",
    },
}


def get_message(code: str, locale: str = "ko") -> str:
    """에러 코드와 locale로 메시지를 조회한다. 없으면 코드 자체를 반환한다."""
    entry = _MESSAGES.get(code, {})
    return entry.get(locale) or entry.get("ko") or code

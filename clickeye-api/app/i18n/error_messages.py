"""에러 코드별 i18n 메시지 레지스트리.

기존 호출처는 그대로 두되, 새 발생 케이스부터 from_key()로 opt-in한다.
admin 전용 엔드포인트는 항상 ko 메시지를 사용한다.
"""

from __future__ import annotations

_MESSAGES: dict[str, dict[str, str]] = {
    "LANGUAGE_INVALID": {
        "ko": "지원하지 않는 언어 코드입니다. 'ko', 'en', 'id', 'ja'만 허용됩니다.",
        "en": "Unsupported language code. Only 'ko', 'en', 'id', and 'ja' are allowed.",
        "id": "Kode bahasa tidak didukung. Hanya 'ko', 'en', 'id', dan 'ja' yang diizinkan.",
        "ja": "サポートされていない言語コードです。'ko'、'en'、'id'、'ja' のみ使用できます。",
    },
    "USER_NOT_FOUND": {
        "ko": "사용자를 찾을 수 없습니다.",
        "en": "User not found.",
        "id": "Pengguna tidak ditemukan.",
        "ja": "ユーザーが見つかりません。",
    },
    "EMAIL_EXISTS": {
        "ko": "이미 등록된 이메일입니다.",
        "en": "Email address is already registered.",
        "id": "Alamat email sudah terdaftar.",
        "ja": "このメールアドレスは既に登録されています。",
    },
    "INVALID_CREDENTIALS": {
        "ko": "이메일 또는 비밀번호가 올바르지 않습니다.",
        "en": "Invalid email or password.",
        "id": "Email atau kata sandi salah.",
        "ja": "メールアドレスまたはパスワードが正しくありません。",
    },
    "USER_INACTIVE": {
        "ko": "비활성화된 계정입니다.",
        "en": "Account is deactivated.",
        "id": "Akun dinonaktifkan.",
        "ja": "アカウントは無効化されています。",
    },
    "INVALID_TOKEN": {
        "ko": "유효하지 않은 토큰입니다.",
        "en": "Invalid token.",
        "id": "Token tidak valid.",
        "ja": "無効なトークンです。",
    },
    "ANTHROPIC_KEY_INVALID_FORMAT": {
        "ko": "올바른 Anthropic API 키 형식이 아닙니다 (sk-ant-... 로 시작해야 합니다).",
        "en": "Invalid Anthropic API key format (must start with sk-ant-...).",
        "id": "Format kunci API Anthropic tidak valid (harus diawali dengan sk-ant-...).",
        "ja": "Anthropic APIキーの形式が正しくありません（sk-ant-... で始まる必要があります）。",
    },
    "CREDENTIALS_NOT_FOUND": {
        "ko": "저장된 자격증명이 없습니다.",
        "en": "No saved credentials found.",
        "id": "Tidak ada kredensial tersimpan.",
        "ja": "保存された認証情報がありません。",
    },
}


def get_message(code: str, locale: str = "ko") -> str:
    """에러 코드와 locale로 메시지를 조회한다. 없으면 코드 자체를 반환한다."""
    entry = _MESSAGES.get(code, {})
    return entry.get(locale) or entry.get("ko") or code


def has_code(code: str) -> bool:
    """해당 에러 코드가 레지스트리에 등록되어 있는지 여부."""
    return code in _MESSAGES

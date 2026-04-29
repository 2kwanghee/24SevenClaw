"""Fernet 대칭 암호화 래퍼 — 사용자 자격증명 저장용."""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _fernet() -> Fernet:
    raw = hashlib.sha256(settings.jwt_secret_key.encode()).digest()
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()

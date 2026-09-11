"""Encryption and redaction utilities for target-system credentials."""

import json
import re
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class SecretConfigurationError(RuntimeError):
    pass


class SecretProtector:
    @staticmethod
    def _fernet() -> Fernet:
        if not settings.AUTH_SECRETS_KEY:
            raise SecretConfigurationError("AUTH_SECRETS_KEY must be configured before storing or using credentials.")
        try:
            return Fernet(settings.AUTH_SECRETS_KEY.encode())
        except (ValueError, TypeError) as exc:
            raise SecretConfigurationError("AUTH_SECRETS_KEY is not a valid Fernet key.") from exc

    @classmethod
    def encrypt(cls, values: dict[str, Any]) -> str:
        return cls._fernet().encrypt(json.dumps(values).encode()).decode()

    @classmethod
    def decrypt(cls, encrypted_value: str) -> dict[str, Any]:
        try:
            value = cls._fernet().decrypt(encrypted_value.encode())
            decoded = json.loads(value)
        except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise SecretConfigurationError("Unable to decrypt test identity credentials.") from exc
        if not isinstance(decoded, dict):
            raise SecretConfigurationError("Decrypted test identity credentials are invalid.")
        return decoded


_SENSITIVE_KEY = re.compile(r"(token|secret|password|authorization|api[_-]?key|cookie|credential)", re.IGNORECASE)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")


def redact(value: Any) -> Any:
    """Return a safe copy suitable for persisted execution evidence and errors."""
    if isinstance(value, dict):
        return {key: "[REDACTED]" if _SENSITIVE_KEY.search(str(key)) else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return _JWT.sub("[REDACTED]", value)
    return value

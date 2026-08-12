"""Standard error response schemas used by every API error handler."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """A field-level validation error safe to display in the client."""

    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """The standard error envelope returned by the API."""

    success: bool = False
    status_code: int
    error_code: str
    user_message: str
    dev_detail: Optional[str] = None
    errors: list[ErrorDetail] = Field(default_factory=list)
    path: Optional[str] = None
    timestamp: str

    @classmethod
    def build(
        cls,
        *,
        status_code: int,
        error_code: str,
        user_message: str,
        dev_detail: Optional[str] = None,
        errors: Optional[list[ErrorDetail]] = None,
        path: Optional[str] = None,
    ) -> "ErrorResponse":
        return cls(
            status_code=status_code,
            error_code=error_code,
            user_message=user_message,
            dev_detail=dev_detail,
            errors=errors or [],
            path=path,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

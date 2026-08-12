"""Global FastAPI exception handlers and the API error contract."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.schemas.error import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


KNOWN_HTTP_ERRORS: dict[str, tuple[str, str]] = {
    "Project not found": ("PROJECT_NOT_FOUND", "Project not found."),
    "Specification not found": ("SPECIFICATION_NOT_FOUND", "Specification not found."),
    "Endpoint not found": ("ENDPOINT_NOT_FOUND", "Endpoint not found."),
    "Only JSON and YAML files are allowed.": (
        "INVALID_SPECIFICATION_FILE",
        "Only JSON and YAML specification files are allowed.",
    ),
    "No test cases found. Please generate test cases first.": (
        "TEST_CASES_NOT_FOUND",
        "No test cases exist for this endpoint. Generate test cases first.",
    ),
    "No endpoints found for this specification.": (
        "ENDPOINTS_NOT_FOUND",
        "No endpoints exist for this specification. Parse the specification first.",
    ),
}

DEFAULT_HTTP_ERRORS: dict[int, tuple[str, str]] = {
    status.HTTP_400_BAD_REQUEST: ("BAD_REQUEST", "The request could not be processed."),
    status.HTTP_401_UNAUTHORIZED: ("UNAUTHORIZED", "Authentication is required."),
    status.HTTP_403_FORBIDDEN: ("FORBIDDEN", "You do not have permission to perform this action."),
    status.HTTP_404_NOT_FOUND: ("NOT_FOUND", "The requested resource was not found."),
    status.HTTP_405_METHOD_NOT_ALLOWED: ("METHOD_NOT_ALLOWED", "This HTTP method is not allowed."),
    status.HTTP_409_CONFLICT: ("CONFLICT", "The request conflicts with the current resource state."),
    status.HTTP_429_TOO_MANY_REQUESTS: ("RATE_LIMITED", "Too many requests. Please try again later."),
}


def _response(error: ErrorResponse) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content=error.model_dump(mode="json"),
    )


def _validation_errors(exc: RequestValidationError) -> list[ErrorDetail]:
    errors: list[ErrorDetail] = []
    for item in exc.errors():
        location = item.get("loc", ())
        field_parts = [str(part) for part in location if part not in {"body", "query", "path", "header"}]
        errors.append(
            ErrorDetail(
                field=".".join(field_parts) or None,
                message=item.get("msg", "Invalid value."),
                code=str(item.get("type", "VALIDATION_ERROR")).upper(),
            )
        )
    return errors


def _http_error_detail(detail: Any, status_code: int) -> tuple[str, str]:
    if isinstance(detail, str) and detail in KNOWN_HTTP_ERRORS:
        return KNOWN_HTTP_ERRORS[detail]

    if status_code >= 500:
        return "INTERNAL_SERVER_ERROR", "An unexpected error occurred."

    return DEFAULT_HTTP_ERRORS.get(
        status_code,
        ("HTTP_ERROR", "The request could not be completed."),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register a single, documented error envelope for all API failures."""

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        error = ErrorResponse.build(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="VALIDATION_ERROR",
            user_message="Please correct the highlighted fields and try again.",
            dev_detail=str(exc) if settings.DEBUG else None,
            errors=_validation_errors(exc),
            path=request.url.path,
        )
        return _response(error)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        error_code, user_message = _http_error_detail(exc.detail, exc.status_code)
        error = ErrorResponse.build(
            status_code=exc.status_code,
            error_code=error_code,
            user_message=user_message,
            dev_detail=str(exc.detail) if settings.DEBUG and exc.status_code >= 500 else None,
            path=request.url.path,
        )
        return _response(error)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        error_code, user_message = _http_error_detail(exc.detail, exc.status_code)
        return _response(
            ErrorResponse.build(
                status_code=exc.status_code,
                error_code=error_code,
                user_message=user_message,
                path=request.url.path,
            )
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API exception on %s", request.url.path)
        error = ErrorResponse.build(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            user_message="An unexpected error occurred.",
            dev_detail=str(exc) if settings.DEBUG else None,
            path=request.url.path,
        )
        return _response(error)

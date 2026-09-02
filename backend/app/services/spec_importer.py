"""Safe import helpers for remote OpenAPI documents and static Swagger UI pages."""

import json
import re
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import yaml

from app.core.config import settings
from app.core.security import validate_target_url


class SpecificationImportError(ValueError):
    pass


class RemoteSpecificationImporter:
    _SWAGGER_URL_PATTERNS = (
        r"\burl\s*:\s*['\"]([^'\"]+)['\"]",
        r"\burls\s*:\s*\[\s*\{\s*url\s*:\s*['\"]([^'\"]+)['\"]",
    )

    @classmethod
    async def fetch(cls, source_url: str, source_kind: str = "auto") -> tuple[bytes, str, str]:
        """Return document content, a safe filename, and its resolved source URL."""
        source_url = validate_target_url(source_url)
        body, content_type = await cls._download(source_url)

        if source_kind == "swagger_ui" or (source_kind == "auto" and cls._looks_like_html(content_type, body)):
            spec_url = cls._discover_swagger_spec_url(source_url, body)
            if not spec_url:
                raise SpecificationImportError(
                    "Swagger UI did not expose a static OpenAPI URL. Provide the direct JSON/YAML specification URL instead."
                )
            source_url = validate_target_url(spec_url)
            body, content_type = await cls._download(source_url)

        extension = cls._detect_extension(source_url, content_type, body)
        cls._validate_openapi_document(body, extension)
        return body, cls._filename_for(source_url, extension), source_url

    @staticmethod
    async def _download(url: str) -> tuple[bytes, str]:
        timeout = httpx.Timeout(settings.SPEC_DOWNLOAD_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            try:
                response = await client.get(url, headers={"Accept": "application/json, application/yaml, text/yaml, text/plain, text/html"})
            except httpx.HTTPError as exc:
                raise SpecificationImportError(f"Unable to download specification: {exc}") from exc

        if response.is_redirect:
            raise SpecificationImportError("Redirects are not followed. Provide the final OpenAPI URL directly.")
        if response.status_code != 200:
            raise SpecificationImportError(f"Specification URL returned HTTP {response.status_code}.")
        if len(response.content) > settings.MAX_SPEC_DOWNLOAD_BYTES:
            raise SpecificationImportError("Specification exceeds the configured download-size limit.")
        return response.content, response.headers.get("content-type", "").lower()

    @staticmethod
    def _looks_like_html(content_type: str, body: bytes) -> bool:
        return "text/html" in content_type or body.lstrip().lower().startswith((b"<!doctype html", b"<html"))

    @classmethod
    def _discover_swagger_spec_url(cls, swagger_url: str, body: bytes) -> str | None:
        try:
            html = body.decode("utf-8")
        except UnicodeDecodeError:
            return None
        for pattern in cls._SWAGGER_URL_PATTERNS:
            match = re.search(pattern, html, flags=re.IGNORECASE)
            if match:
                return urljoin(swagger_url, match.group(1))
        return None

    @staticmethod
    def _detect_extension(url: str, content_type: str, body: bytes) -> str:
        suffix = PurePosixPath(urlparse(url).path).suffix.lower()
        if suffix in {".json", ".yaml", ".yml"}:
            return suffix
        if "json" in content_type or body.lstrip().startswith((b"{", b"[")):
            return ".json"
        return ".yaml"

    @staticmethod
    def _validate_openapi_document(body: bytes, extension: str) -> None:
        try:
            parsed: Any = json.loads(body) if extension == ".json" else yaml.safe_load(body)
        except (json.JSONDecodeError, yaml.YAMLError, UnicodeDecodeError) as exc:
            raise SpecificationImportError("URL did not return valid JSON or YAML.") from exc

        if not isinstance(parsed, dict) or not isinstance(parsed.get("paths"), dict):
            raise SpecificationImportError("Document is not a valid OpenAPI/Swagger specification: missing 'paths'.")
        if not (parsed.get("openapi") or parsed.get("swagger")):
            raise SpecificationImportError("Document is missing the OpenAPI or Swagger version field.")

    @staticmethod
    def _filename_for(url: str, extension: str) -> str:
        filename = PurePosixPath(urlparse(url).path).name
        if not filename or PurePosixPath(filename).suffix.lower() not in {".json", ".yaml", ".yml"}:
            filename = f"remote_openapi{extension}"
        return filename

"""Runtime-only target API authentication. Credentials never enter scenarios or jobs."""

import asyncio
import base64
from typing import Any

import httpx
from jsonpath_ng import parse

from app.models.auth_profile import AuthProfile, TestIdentity
from app.services.secrets import SecretConfigurationError, SecretProtector


class AuthenticationError(RuntimeError):
    pass


class AuthSession:
    def __init__(self, profile: AuthProfile, identity: TestIdentity, base_url: str):
        self.profile = profile
        self.identity = identity
        self.base_url = base_url.rstrip("/")
        self.secrets = SecretProtector.decrypt(identity.encrypted_secret)
        self.headers: dict[str, str] = {}
        self.query_params: dict[str, Any] = {}
        self.cookies: dict[str, str] = {}
        self._refresh_token: str | None = None
        self._lock = asyncio.Lock()

    async def authenticate(self, client: httpx.AsyncClient) -> None:
        async with self._lock:
            if self.profile.auth_type == "login":
                await self._login(client)
            else:
                self._apply_static_credentials()

    def request_components(self) -> tuple[dict[str, str], dict[str, Any], dict[str, str]]:
        return dict(self.headers), dict(self.query_params), dict(self.cookies)

    async def reauthenticate_after_unauthorized(self, client: httpx.AsyncClient) -> None:
        # Login is re-run on 401. Static credential profiles cannot refresh themselves.
        if self.profile.auth_type != "login":
            return
        async with self._lock:
            try:
                if self._refresh_token and (self.profile.login_config or {}).get("refresh_path"):
                    await self._refresh(client)
                    return
            except AuthenticationError:
                pass
            await self._login(client)

    def _apply_static_credentials(self) -> None:
        rules = self.profile.injection_rules or {}
        target = rules.get("target", "header")
        name = rules.get("name")
        if not name:
            raise AuthenticationError("Authentication injection rules require a name.")

        if self.profile.auth_type == "bearer":
            value = f"{rules.get('prefix', 'Bearer ')}{self.secrets.get('token', '')}"
        elif self.profile.auth_type == "api_key":
            value = str(self.secrets.get("api_key", ""))
        elif self.profile.auth_type == "basic":
            encoded = base64.b64encode(
                f"{self.secrets.get('username', '')}:{self.secrets.get('password', '')}".encode()
            ).decode()
            value = f"Basic {encoded}"
        else:
            raise AuthenticationError(f"Unsupported auth type: {self.profile.auth_type}")

        if not value or value.endswith(" "):
            raise AuthenticationError("Test identity is missing required authentication credentials.")
        self._inject(target, name, value)

    async def _login(self, client: httpx.AsyncClient) -> None:
        config = self.profile.login_config or {}
        payload = dict(config.get("payload_template") or {})
        payload[config.get("username_field", "username")] = self.secrets.get("username")
        payload[config.get("password_field", "password")] = self.secrets.get("password")
        if payload.get(config.get("username_field", "username")) is None or payload.get(config.get("password_field", "password")) is None:
            raise AuthenticationError("Login identity requires username and password secrets.")

        try:
            response = await client.request(
                method=config.get("method", "POST").upper(),
                url=f"{self.base_url}{config['login_path']}",
                json=payload,
            )
            response.raise_for_status()
            response_data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthenticationError("Automatic login failed; verify the login endpoint and test identity.") from exc

        token = self._json_path_value(response_data, config.get("access_token_json_path", "$.access_token"))
        if not token:
            raise AuthenticationError("Login response did not contain the configured access token.")
        rules = self.profile.injection_rules or {"target": "header", "name": "Authorization", "prefix": "Bearer "}
        self._inject(rules.get("target", "header"), rules.get("name", "Authorization"), f"{rules.get('prefix', 'Bearer ')}{token}")
        refresh_path = config.get("refresh_token_json_path")
        if refresh_path:
            self._refresh_token = self._json_path_value(response_data, refresh_path)

        if config.get("cookie_names"):
            for cookie_name in config["cookie_names"]:
                if cookie_name in response.cookies:
                    self.cookies[cookie_name] = response.cookies[cookie_name]

    async def _refresh(self, client: httpx.AsyncClient) -> None:
        config = self.profile.login_config or {}
        payload = {
            config.get("refresh_token_field", "refresh_token"): self._refresh_token,
        }
        try:
            response = await client.request(
                method=config.get("refresh_method", "POST").upper(),
                url=f"{self.base_url}{config['refresh_path']}",
                json=payload,
            )
            response.raise_for_status()
            response_data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthenticationError("Token refresh failed.") from exc

        token = self._json_path_value(response_data, config.get("refresh_access_token_json_path", config.get("access_token_json_path", "$.access_token")))
        if not token:
            raise AuthenticationError("Refresh response did not contain the configured access token.")
        rules = self.profile.injection_rules or {"target": "header", "name": "Authorization", "prefix": "Bearer "}
        self._inject(rules.get("target", "header"), rules.get("name", "Authorization"), f"{rules.get('prefix', 'Bearer ')}{token}")
        refresh_path = config.get("refresh_token_json_path")
        if refresh_path:
            self._refresh_token = self._json_path_value(response_data, refresh_path) or self._refresh_token

    @staticmethod
    def _json_path_value(data: Any, json_path: str) -> Any:
        matches = parse(json_path).find(data)
        return matches[0].value if matches else None

    def _inject(self, target: str, name: str, value: str) -> None:
        if target == "header":
            self.headers[name] = value
        elif target == "query":
            self.query_params[name] = value
        elif target == "cookie":
            self.cookies[name] = value
        else:
            raise AuthenticationError("Authentication target must be header, query, or cookie.")


def build_auth_session(profile: AuthProfile | None, identity: TestIdentity | None, base_url: str) -> AuthSession | None:
    if profile is None and identity is None:
        return None
    if profile is None or identity is None:
        raise AuthenticationError("Both an auth profile and test identity are required.")
    try:
        return AuthSession(profile, identity, base_url)
    except SecretConfigurationError as exc:
        raise AuthenticationError(str(exc)) from exc

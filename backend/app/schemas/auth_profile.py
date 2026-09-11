from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


AuthType = Literal["login", "bearer", "api_key", "basic"]


class AuthProfileCreate(BaseModel):
    environment_id: int
    name: str = Field(min_length=1, max_length=100)
    auth_type: AuthType
    injection_rules: dict[str, Any] = Field(default_factory=dict)
    login_config: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_auth_configuration(self):
        if self.auth_type == "login" and (not self.login_config or not self.login_config.get("login_path")):
            raise ValueError("login auth profiles require login_config.login_path.")
        return self


class AuthProfileResponse(BaseModel):
    id: int
    environment_id: int
    name: str
    auth_type: AuthType
    injection_rules: dict[str, Any]
    login_config: dict[str, Any] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestIdentityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    role: str | None = Field(default=None, max_length=100)
    secrets: dict[str, Any] = Field(min_length=1)


class TestIdentityResponse(BaseModel):
    id: int
    auth_profile_id: int
    name: str
    role: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

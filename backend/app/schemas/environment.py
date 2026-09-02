from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.security import validate_target_url


class ProjectEnvironmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    base_url: str
    is_production: bool = False
    verify_tls: bool = True

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return validate_target_url(value).rstrip("/")


class ProjectEnvironmentResponse(ProjectEnvironmentCreate):
    id: int
    project_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

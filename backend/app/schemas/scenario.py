from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional

class ExtractRule(BaseModel):
    json_path: str = Field(..., description = "JSONPath expression used to extract data from the response. such as '$.id' or '$.access_token'")
    save_as: str = Field(..., description = "Name of the variable to extract value will be stored in memory, such as 'created_user_id'")


class InjectRule(BaseModel):
    target: str = Field(..., description = "Part of the request where the value should be inserted: 'path', 'query', 'payload', or 'header'")
    field: str = Field(..., description = "Name of the field or parameter that should be replaced, such as 'uuid' or 'Authorization'")
    use_memory: str = Field(..., description = "Name of the value stored in memory that should be used, such as 'created_user_id'")


class ScenarioStepCreate(BaseModel):
    endpoint_method: str = Field(description="HTTP method used by the endpoint, such as 'POST','GET','PUT',or 'DELETE'")
    endpoint_path: str = Field(
        description = "API endpoint path, such as '/api/users'"
    )
    payload: Optional[Dict[str, Any]] = Field(
        default = None,
        description = "Request body dat sent to the API"
    )
    extract_rules: Optional[List[ExtractRule]] = Field(
        default = None,
        description = "Rules used to extract values from the API response and store them in memory"
    )
    inject_rules: Optional[List[InjectRule]] = Field(
        default = None,
        description = "Rules used to take values from memory and insert them into the next request"
    )
    expected_status: int = Field(
        description = "HTTP status code that is expected from the API response"
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_ai_field_names(cls, value: Any) -> Any:
        """Accept common LLM synonyms before structured-output validation.

        The persisted model intentionally uses endpoint_* and payload.  Models
        frequently return the more conversational method/path/request_body
        names, so normalize those names instead of rejecting an otherwise
        usable scenario plan.
        """
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        aliases = {
            "method": "endpoint_method",
            "path": "endpoint_path",
            "request_body": "payload",
        }
        for source, target in aliases.items():
            if target not in normalized and source in normalized:
                normalized[target] = normalized[source]

        # This is only a safety net for imperfect model output.  The prompt
        # below still requires the model to supply an explicit status code.
        normalized.setdefault("expected_status", 200)
        return normalized


class TestScenarioCreate(BaseModel):
    name: str = Field(
        description = "Name of the test scenario, such as 'User Registration and Deletion Flow'"
    )
    description: str
    steps: List[ScenarioStepCreate]

    @model_validator(mode="before")
    @classmethod
    def supply_description_for_legacy_ai_output(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        normalized.setdefault(
            "description",
            f"Stateful API workflow: {normalized.get('name', 'AI-generated scenario')}.",
        )
        return normalized


class AITestScenarioPlan(BaseModel):
    scenarios: List[TestScenarioCreate]

from pydantic import BaseModel, Field
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


class TestScenarioCreate(BaseModel):
    name: str = Field(
        description = "Name of the test scenario, such as 'User Registration and Deletion Flow'"
    )
    description: str
    steps: List[ScenarioStepCreate]


class AITestScenarioPlan(BaseModel):
    scenarios: List[TestScenarioCreate]
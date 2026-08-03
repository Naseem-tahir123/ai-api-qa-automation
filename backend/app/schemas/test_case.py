from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional


class AIGeneratedTestCase(BaseModel):
    category: str = Field(description = "Category of the test: 'Positive', 'Negative', or 'Boundary'")
    description: str = Field(description = "Clear Explanation of What this test case verifies")
    payload: Optional[Dict[str, Any]] = Field(description = "The exact JSON body sent to the API")
    path_params: Optional[Dict[str, Any]] = Field(default=None, description = "Values for URL  path parameters (e.g., {uuid})")
    query_params: Optional[Dict[str, Any]] = Field(default = None, description = "Values for URL query parameters")
    expected_status: int = Field(description = "The expected status code e.g., 200,201, 400")


class AITestPlan(BaseModel):
    test_cases: List[AIGeneratedTestCase]


class TestCaseResponse(BaseModel):
    id: int
    endpoint_id: int
    category: str
    description: str
    payload: Optional[Dict[str, Any]] 
    path_params: Optional[Dict[str, Any]]
    query_params: Optional[Dict[str, Any]]
    expected_status: int


    model_config = ConfigDict(from_attributes=True)
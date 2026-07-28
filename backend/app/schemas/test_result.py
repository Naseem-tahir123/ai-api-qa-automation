from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any, List

class TestResultResponse(BaseModel):
    id: int
    test_case_id: int
    actual_status: Optional[int]
    is_passed: bool
    response_body: Optional[Any]
    execution_time_ms: Optional[float]
    error_message: Optional[str]
    executed_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ExecutionSummary(BaseModel):
    endpoint_id: int
    total_executed: int
    passed: int
    failed: int
    results: List[TestResultResponse]
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# 1. Actionable Bug Report (For Developer)
class FailureDetail(BaseModel):
    endpoint_path: str
    method: str
    test_category: str
    description: str
    payload_sent: Optional[Dict[str, Any]]
    expected_status: int
    actual_status: Optional[int]
    error_message: Optional[str]

# 2. Endpoint Health Summary
class EndpointSummary(BaseModel):
    endpoint_id: int
    path: str
    method: str
    total_tests: int
    passed: int
    failed: int
    avg_execution_time_ms: float

class TestEvidence(BaseModel):
    id: int
    endpoint_path: str
    method: str
    category: str
    description: str
    expected_status: int
    actual_status: Optional[int]
    is_passed: bool
    execution_time_ms: Optional[float]
    reason: str
    error_message: Optional[str]

# 3. Master QA Report
class ProjectQA_Report(BaseModel):
    project_id: int
    spec_id: int
    
    # Coverage Metrics
    total_endpoints_in_spec: int
    tested_endpoints: int
    coverage_percentage: float
    
    # Execution Metrics
    total_tests_executed: int
    total_passed: int
    total_failed: int
    pass_rate_percentage: float
    total_execution_time_ms: float
    
    # Category Breakdown (e.g., Positive: 10, Negative: 5)
    category_breakdown: Dict[str, Dict[str, int]]
    
    # Detailed Data
    endpoint_details: List[EndpointSummary]
    actionable_failures: List[FailureDetail]
    test_evidence: List[TestEvidence]

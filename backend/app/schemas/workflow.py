from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CaptureRule(BaseModel):
    context_key: str
    selectors: List[str]


class InjectionRule(BaseModel):
    target: str
    context_key: str


class WorkflowStepResponse(BaseModel):
    id: int
    endpoint_id: int
    position: int
    name: str
    depends_on: List[int]
    capture_rules: List[Dict[str, Any]]
    injection_rules: List[Dict[str, Any]]
    is_cleanup: bool
    model_config = ConfigDict(from_attributes=True)


class WorkflowPlanResponse(BaseModel):
    id: int
    specification_id: int
    name: str
    status: str
    graph: Dict[str, Any]
    created_at: datetime
    steps: List[WorkflowStepResponse]
    model_config = ConfigDict(from_attributes=True)


class WorkflowExecutionRequest(BaseModel):
    target_base_url: str
    auth_config: Dict[str, str] = Field(default_factory=dict)
    stop_on_failure: bool = True
    run_cleanup: bool = True


class WorkflowRunResponse(BaseModel):
    id: int
    plan_id: int
    status: str
    runtime_context: Dict[str, Any]
    step_results: List[Dict[str, Any]]
    summary: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class WorkflowReportResponse(BaseModel):
    plan_id: int
    run_id: int
    workflow_status: str
    summary: Dict[str, Any]
    dependency_graph: Dict[str, Any]
    runtime_context: Dict[str, Any]
    step_results: List[Dict[str, Any]]
    root_causes: List[Dict[str, Any]]
    recommendations: List[str]

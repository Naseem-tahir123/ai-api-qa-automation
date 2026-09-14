from types import SimpleNamespace

from app.services.workflow_executor import WorkflowExecutor
from app.services.workflow_planner import WorkflowPlanner


def endpoint(endpoint_id: int, method: str, path: str):
    return SimpleNamespace(id=endpoint_id, method=method, path=path, summary=None)


def test_planner_captures_and_reuses_real_resource_id():
    endpoints = [
        endpoint(3, "DELETE", "/api/v1/users/{user_id}"),
        endpoint(2, "GET", "/api/v1/users/{user_id}"),
        endpoint(1, "POST", "/api/v1/users"),
    ]

    steps, graph = WorkflowPlanner.build(endpoints)

    assert [step.endpoint.id for step in steps] == [1, 2, 3]
    assert steps[0].capture_rules[0]["context_key"] == "user.id"
    assert steps[1].depends_on_endpoint_ids == [1]
    assert steps[1].injection_rules == [{"target": "path.user_id", "context_key": "user.id"}]
    assert steps[2].is_cleanup is True
    assert {"from": 1, "to": 2} in graph["edges"]


def test_executor_injects_captured_value_into_path():
    step = SimpleNamespace(
        endpoint=endpoint(2, "GET", "/users/{user_id}"),
        injection_rules=[{"target": "path.user_id", "context_key": "user.id"}],
    )
    case = SimpleNamespace(payload=None, query_params={}, path_params={"user_id": "dummy-uuid"})

    path, payload, query = WorkflowExecutor._inject(step, case, {"user.id": "real-123"})

    assert path == "/users/real-123"
    assert payload == {}
    assert query == {}


def test_response_selector_supports_wrapped_response_data():
    response = {"data": {"id": "real-456"}}

    assert WorkflowExecutor._read_selector(response, "$.data.id") == "real-456"
    assert WorkflowExecutor._read_selector(response, "$.missing.id") is None

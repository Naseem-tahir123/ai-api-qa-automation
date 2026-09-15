# backend/app/services/workflow_executor.py

import time
import httpx
import asyncio
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from jsonpath_ng import parse
from app.services.auth_runtime import AuthSession
from app.services.secrets import redact

def _failure_classification(status: int | None, error: str | None) -> str | None:
    if error:
        return "network_error"
    if status in {401, 403}:
        return "authentication_failure"
    if status and 500 <= status:
        return "server_error"
    if status and 400 <= status:
        return "validation_failure"
    return "contract_mismatch" if status is not None else None

# =========================================================================
# 1. STATE DEFINITION (Global Memory & Tracking)
# =========================================================================
class PipelineState(TypedDict):
    pipeline_id: int
    steps: List[Dict[str, Any]]
    memory: Dict[str, Any]
    results: List[Dict[str, Any]]
    setup_failed: bool             # Flag to track if setup crashed
    cleanup_warnings: List[str]    # To track teardown failures
    base_url: str
    verify_tls: bool
    auth_session: AuthSession | None

# =========================================================================
# 2. HELPER: SINGLE STEP EXECUTOR
# =========================================================================
async def _execute_single_step(step: Dict[str, Any], memory: Dict[str, Any], base_url: str, auth_session: AuthSession | None, client: httpx.AsyncClient) -> Dict[str, Any]:
    method = step.get("endpoint_method", "GET").upper()
    path = step.get("endpoint_path", "")
    payload = step.get("payload") or {}
    params = step.get("query_params") or {}
    headers = {}

    auth_headers, auth_params, auth_cookies = {}, {}, {}
    if auth_session:
        auth_headers, auth_params, auth_cookies = auth_session.request_components()
        headers.update(auth_headers)
        params.update(auth_params)

    # --- INJECT RULES (Memory to Request) ---
    inject_rules = step.get("inject_rules") or []
    for rule in inject_rules:
        mem_val = memory.get(rule["use_memory"])
        if mem_val is None:
            continue
            
        target = rule.get("target", "path").lower()
        field = rule.get("field", "")

        if target == "path":
            path = path.replace(f"{{{field}}}", str(mem_val))
        elif target == "query":
            params[field] = mem_val
        elif target == "header":
            headers[field] = str(mem_val)
        elif target == "payload":
            payload[field] = mem_val

    full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    start_time = time.time()
    actual_status, response_data, error_msg = None, None, None

    # --- EXECUTE REQUEST ---
    try:
        response = await client.request(
            method=method,
            url=full_url,
            json=payload if payload and method in ["POST", "PUT", "PATCH"] else None,
            params=params if params else None,
            headers=headers if headers else None,
            cookies=auth_cookies or None,
        )
        # Re-login only after 401 and retry only idempotent/safe requests.
        if response.status_code == 401 and auth_session and method in {"GET", "HEAD", "OPTIONS"}:
            await auth_session.reauthenticate_after_unauthorized(client)
            refreshed_headers, refreshed_params, refreshed_cookies = auth_session.request_components()
            headers.update(refreshed_headers)
            params.update(refreshed_params)
            response = await client.request(
                method=method,
                url=full_url,
                params=params if params else None,
                headers=headers if headers else None,
                cookies=refreshed_cookies or None,
            )
        actual_status = response.status_code
        try:
            response_data = response.json()
        except Exception:
            response_data = {"raw_text": response.text[:500]}

        # --- EXTRACT RULES (Response to Memory) ---
        extract_rules = step.get("extract_rules") or []
        if actual_status in (200, 201) and isinstance(response_data, dict):
            for rule in extract_rules:
                try:
                    jsonpath_expr = parse(rule["json_path"])
                    match = jsonpath_expr.find(response_data)
                    if match:
                        memory[rule["save_as"]] = match[0].value
                except Exception:
                    pass
    except Exception as e:
        error_msg = redact(f"Request Failed: {str(e)}")

    expected_status = step.get("expected_status")
    is_passed = (actual_status == expected_status)

    return {
        "scenario_step_id": step.get("id"),
        "actual_status": actual_status,
        "is_passed": is_passed,
        "response_body": redact(response_data),
        "execution_time_ms": round((time.time() - start_time) * 1000, 2),
        "error_message": error_msg
        ,"failure_classification": None if is_passed else _failure_classification(actual_status, error_msg)
        ,"request_metadata": redact({"method": method, "path": path, "query": params, "headers": headers})
        ,"response_metadata": redact({"status": actual_status})
    }

# =========================================================================
# 3. LANGGRAPH NODES (The 3 Layers)
# =========================================================================
async def node_setup(state: PipelineState) -> PipelineState:
    """LAYER 1: Run setup steps sequentially."""
    setup_steps = [s for s in state["steps"] if s.get("step_type") == "setup"]
    
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False, verify=state["verify_tls"]) as client:
        for step in setup_steps:
            result = await _execute_single_step(step, state["memory"], state["base_url"], state["auth_session"], client)
            state["results"].append(result)
            
            if not result["is_passed"]:
                state["setup_failed"] = True
                break # Fast-Fail: Stop setup if one fails
    return state

async def node_test(state: PipelineState) -> PipelineState:
    """LAYER 2: Run tests. Parallel for safe tests, sequential for mutating ones."""
    if state.get("setup_failed"):
        return state # Skip tests if setup failed
        
    test_steps = [s for s in state["steps"] if s.get("step_type") == "test"]
    safe_tests = [s for s in test_steps if not s.get("mutates_state")]
    mutating_tests = [s for s in test_steps if s.get("mutates_state")]
    
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False, verify=state["verify_tls"]) as client:
        # ⚡ 1. Run Safe Tests in Parallel (Ultra Fast)
        tasks = [_execute_single_step(step, state["memory"], state["base_url"], state["auth_session"], client) for step in safe_tests]
        safe_results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in safe_results:
            if isinstance(res, dict): state["results"].append(res)
            
        # 🐢 2. Run Mutating Tests Sequentially (Safe)
        for step in mutating_tests:
            result = await _execute_single_step(step, state["memory"], state["base_url"], state["auth_session"], client)
            state["results"].append(result)

    return state

async def node_teardown(state: PipelineState) -> PipelineState:
    """LAYER 3: Cleanup. Runs even if tests fail."""
    teardown_steps = [s for s in state["steps"] if s.get("step_type") == "teardown"]
    
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=False, verify=state["verify_tls"]) as client:
        for step in teardown_steps:
            result = await _execute_single_step(step, state["memory"], state["base_url"], state["auth_session"], client)
            state["results"].append(result)
            
            if not result["is_passed"]:
                state["cleanup_warnings"].append(f"Teardown failed for path: {step.get('endpoint_path')}")
    return state

# =========================================================================
# 4. GRAPH ROUTING & COMPILATION
# =========================================================================
def route_after_setup(state: PipelineState) -> str:
    if state.get("setup_failed"):
        return "teardown" # Skip tests, jump to cleanup
    return "test"

workflow = StateGraph(PipelineState)
workflow.add_node("setup", node_setup)
workflow.add_node("test", node_test)
workflow.add_node("teardown", node_teardown)

workflow.set_entry_point("setup")
workflow.add_conditional_edges("setup", route_after_setup)
workflow.add_edge("test", "teardown")
workflow.add_edge("teardown", END)

unified_pipeline_app = workflow.compile()

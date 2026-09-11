import time
import httpx
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from jsonpath_ng import parse

# 1. STATE DEFINITION (The Memory of our Workflow)
class WorkflowState(TypedDict):
    scenario_id: int
    steps: List[Dict[str, Any]] # List of steps to execute
    current_step_index: int     # Which step are we on?
    memory: Dict[str, Any]      # The Global Memory for Extract/Inject
    results: List[Dict[str, Any]]# Store pass/fail results
    base_url: str
    auth_config: dict


# 2. THE EXECUTION NODE (The worker that does the actual HTTP call)
async def execute_step(state: WorkflowState) -> WorkflowState:
    step = state["steps"][state["current_step_index"]]
    memory = state["memory"]

    # Pre-process details
    method = step.get("method", "GET").upper()
    path = step.get("path","")
    payload = step.get("payload") or {}
    params = step.get("query_params") or {}
    headers = {}

    # Setup base Auth if provided
    auth_config = state.get("auth_config",{})
    if auth_config.get("token"):
        headers["Authorization"] = f"Bearer {auth_config['token']}"

    # --- A. INJECT RULES (Put data from Memory INTO Request) ---
    inject_rules = step.get("inject_rules") or []
    for rule in inject_rules:
        mem_val = memory.get(rule["use_memory"])
        if mem_val is None:
            continue # If value not found in memory , skip
        target = rule.get("target", "path").lower()
        field = rule.get("field","")

        if target =="path":
            # Example: /users/{id} -> /users/42
            path = path.replace(f"{{{field}}}", str(mem_val))
        elif target == "query":
            params[field] = mem_val
        elif target == "header":
            headers[field] = str(mem_val)
        elif target == "payload":
            payload[field] = mem_val
    # Construct final URL
    full_url = f"{state['base_url'].rstrip('/')}{path}"

    start_time = time.time()
    actual_status = None
    response_data = None
    error_msg = None

    #--- B. EXECUTE HTTP REQUEST ---
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            response = await client.request(
                method = method,
                url = full_url,
                json = payload if payload and method in ["POST","PUT","PATCH"] else None,
                params = params if params else None,
                headers=headers if headers else None
            )

            actual_status = response.status_code
            try:
                response_data = response.json()
            except Exception:
                response_data = {"raw_text": response.text[:500]}


            # ---C. EXTRACT RULES (Get data FROM Response into Memory) ---
            extract_rules = step.get("extract_rules") or []
            if actual_status in (200,201) and isinstance(response_data, dict):
                for rule in extract_rules:
                    try:
                        jsonpath_expr = parse(rule["json_path"])
                        match = jsonpath_expr.find(response_data)
                        if match:
                            # Save the extracted value into our Global Memory!
                            state["memory"][rule["save_as"]] = match[0].value
                    except Exception as parse_err:
                        print(f"Extraction failed for {rule['json_path']}: {parse_err}")

    except Exception as e:
        error_msg = str(e)

        
    execution_time = (time.time() - start_time) * 1000
    expected_status = step.get("expected_status")
    is_passed = (actual_status == expected_status)


    # Save Result
    result_record ={
        "step_order": step.get("step_order"),
        "method": method,
        "path": path,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "is_passed": is_passed,
        "response_body": response_data,
        "execution_time_ms": round(execution_time, 2),
        "error_message":error_msg
    }
    state["results"].append(result_record)

    # Move to next step
    state["current_step_index"] += 1

    return state


# =========================================================================
# 3. ROUTER (Decides if we should go to next step or End)
# =========================================================================
def should_continue(state: WorkflowState) -> str:
    """If there are more steps, continue executing. Else END."""
    if state["current_step_index"] < len(state["steps"]):
        return "execute"
    return END


# =========================================================================
# 4. GRAPH COMPILATION
# =========================================================================
workflow = StateGraph(WorkflowState)

# Add our single powerful node
workflow.add_node("execute", execute_step)

# Set starting point
workflow.set_entry_point("execute")

# Add conditional routing (Looping)
workflow.add_conditional_edges("execute", should_continue)

# Compile the graph into a runnable application
scenario_executor_app = workflow.compile()
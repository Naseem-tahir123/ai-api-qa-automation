"""Policy-driven, deterministic test intent selection and coverage reporting."""
from typing import Any

POLICY_VERSION = "coverage/v1"

def intents_for(endpoint: dict[str, Any]) -> list[dict[str, Any]]:
    method, action, protected = endpoint["method"], endpoint["action"], endpoint["access"] == "protected"
    intents = [{"intent": "happy_path", "priority": "high", "ai_required": False, "assertions": ["expected_status", "contract"]},
               {"intent": "contract_status", "priority": "high", "ai_required": False, "assertions": ["response_schema"]}]
    if action == "write":
        intents += [{"intent": "required_field_validation", "priority": "high", "ai_required": False, "assertions": ["4xx"]},
                    {"intent": "type_format_validation", "priority": "medium", "ai_required": False, "assertions": ["4xx"]},
                    {"intent": "boundary", "priority": "medium", "ai_required": False, "assertions": ["4xx"]}]
    if protected:
        intents.append({"intent": "authorization_rbac", "priority": "high", "ai_required": False, "assertions": ["401_or_403"]})
    if method == "GET":
        parameter_names = {p.get("name", "") for p in endpoint.get("parameters", [])}
        if parameter_names & {"page", "limit", "offset", "cursor", "filter", "sort"}:
            intents.append({"intent": "pagination_filtering", "priority": "medium", "ai_required": False, "assertions": ["pagination_contract"]})
    if method in {"PUT", "DELETE"}:
        intents.append({"intent": "idempotency", "priority": "medium", "ai_required": False, "assertions": ["repeat_safe"]})
    if endpoint["high_risk"]:
        intents.append({"intent": "regression", "priority": "critical", "ai_required": False, "assertions": ["stable_contract"]})
    return intents


def plan_coverage(qa_ir: dict[str, Any]) -> dict[str, Any]:
    rows = []
    selected = []
    for endpoint in qa_ir["endpoints"]:
        endpoint_key = f"{endpoint['method']} {endpoint['path']}"
        intents = intents_for(endpoint)
        selected.extend({"endpoint_id": endpoint["id"], "endpoint": endpoint_key, **intent} for intent in intents)
        rows.append({"endpoint": endpoint_key, "resource": endpoint["resource"],
                     "coverage": {intent["intent"]: "planned" for intent in intents}})
    return {"policy_version": POLICY_VERSION, "qa_ir_fingerprint": qa_ir["fingerprint"],
            "selected_intents": selected, "coverage_matrix": rows,
            "gaps": [{"endpoint": row["endpoint"], "status": "not_executed"} for row in rows]}

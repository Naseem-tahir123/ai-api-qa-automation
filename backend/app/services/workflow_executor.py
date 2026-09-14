import copy
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowPlan, WorkflowRun


class WorkflowExecutor:
    @staticmethod
    def _read_selector(response: Any, selector: str) -> Any:
        value = response
        for part in selector.removeprefix("$.").split("."):
            if not isinstance(value, dict) or part not in value: return None
            value = value[part]
        return value

    @staticmethod
    def _inject(step, test_case, context: dict[str, Any]) -> tuple[str, dict, dict]:
        path = step.endpoint.path
        payload = copy.deepcopy(test_case.payload or {})
        query = copy.deepcopy(test_case.query_params or {})
        path_params = copy.deepcopy(test_case.path_params or {})
        for rule in step.injection_rules or []:
            value = context.get(rule["context_key"])
            if value is None: raise ValueError(f"Missing runtime value: {rule['context_key']}")
            target_type, key = rule["target"].split(".", 1)
            if target_type == "path": path_params[key] = value
            elif target_type == "query": query[key] = value
            elif target_type == "body": payload[key] = value
        for key, value in path_params.items(): path = path.replace(f"{{{key}}}", str(value))
        return path, payload, query

    @classmethod
    async def execute(cls, plan: WorkflowPlan, target_base_url: str, auth_config: dict, stop_on_failure: bool, run_cleanup: bool, db: AsyncSession) -> WorkflowRun:
        run = WorkflowRun(plan_id=plan.id, status="running", runtime_context={}, step_results=[], summary={})
        db.add(run); await db.flush()
        context: dict[str, Any] = {}
        trace: list[dict[str, Any]] = []
        blocked_steps: set[int] = set()
        halt_non_cleanup = False

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
            for step in plan.steps:
                if step.is_cleanup and not run_cleanup: continue
                if halt_non_cleanup and not step.is_cleanup:
                    trace.append({"step_id": step.id, "endpoint_id": step.endpoint_id, "status": "blocked", "reason": "Execution stopped after an earlier workflow failure."})
                    blocked_steps.add(step.id)
                    continue
                if any(dependency in blocked_steps for dependency in step.depends_on or []):
                    trace.append({"step_id": step.id, "status": "blocked", "reason": "An upstream dependency failed."}); blocked_steps.add(step.id); continue
                positive_cases = [case for case in step.endpoint.test_cases if any(word in case.category.lower() for word in ("positive", "happy", "success"))]
                test_case = positive_cases[0] if positive_cases else (step.endpoint.test_cases[0] if step.endpoint.test_cases else None)
                if not test_case:
                    trace.append({"step_id": step.id, "endpoint_id": step.endpoint_id, "status": "blocked", "reason": "No generated test case is available."}); blocked_steps.add(step.id); continue
                started = time.perf_counter()
                try:
                    path, payload, query = cls._inject(step, test_case, context)
                    headers = {}
                    if auth_config.get("token"):
                        headers["Authorization"] = f"Bearer {auth_config['token']}"
                    if auth_config.get("api_key"):
                        headers[auth_config.get("api_key_header", "X-API-Key")] = auth_config["api_key"]
                    response = await client.request(step.endpoint.method, f"{target_base_url.rstrip('/')}{path}", json=payload or None, params=query or None, headers=headers)
                    try: response_body = response.json()
                    except Exception: response_body = {"raw_text": response.text[:500]}
                    passed = response.status_code == test_case.expected_status
                    captured = {}
                    if passed:
                        for rule in step.capture_rules or []:
                            for selector in rule.get("selectors", []):
                                value = cls._read_selector(response_body, selector)
                                if value is not None: context[rule["context_key"]] = value; captured[rule["context_key"]] = value; break
                    result = {"step_id": step.id, "endpoint_id": step.endpoint_id, "method": step.endpoint.method, "path": path, "status": "passed" if passed else "failed", "expected_status": test_case.expected_status, "actual_status": response.status_code, "duration_ms": round((time.perf_counter() - started) * 1000, 2), "captured": captured, "reason": "Expected status received." if passed else f"Expected HTTP {test_case.expected_status}, received HTTP {response.status_code}."}
                    trace.append(result)
                    if not passed: blocked_steps.add(step.id)
                except Exception as exc:
                    trace.append({"step_id": step.id, "endpoint_id": step.endpoint_id, "method": step.endpoint.method, "path": step.endpoint.path, "status": "failed", "actual_status": None, "duration_ms": round((time.perf_counter() - started) * 1000, 2), "reason": str(exc)}); blocked_steps.add(step.id)
                if stop_on_failure and step.id in blocked_steps and not step.is_cleanup:
                    halt_non_cleanup = True

        passed = sum(item["status"] == "passed" for item in trace)
        failed = sum(item["status"] == "failed" for item in trace)
        blocked = sum(item["status"] == "blocked" for item in trace)
        run.status = "passed" if failed == 0 and blocked == 0 else "failed"
        run.runtime_context = context; run.step_results = trace
        run.summary = {"total_steps": len(trace), "passed": passed, "failed": failed, "blocked": blocked, "workflow_pass_rate": round(passed / len(trace) * 100, 2) if trace else 0}
        run.completed_at = datetime.now(timezone.utc)
        await db.commit(); await db.refresh(run)
        return run

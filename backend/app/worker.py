import json
import re
import time
from arq.connections import RedisSettings
from sqlalchemy import delete
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.database import AsyncSessionLocal
from app.models.auth_profile import AuthProfile, TestIdentity
from app.models.qa_artifacts import CoveragePlan, QAIRSnapshot
from app.models.scenario import ScenarioStep, TestScenario
from app.models.specification import APISpecification
from app.models.test_result import TestResult
from app.services.ai_generator import get_ai_generator
from app.services.auth_runtime import AuthenticationError, build_auth_session
from app.services.coverage_planner import plan_coverage
from app.services.qa_ir import build_qa_ir
from app.services.workflow_executor import unified_pipeline_app


# ---------------------------------------------------------
# HELPER: ROBUST ENDPOINT MATCHING
# ---------------------------------------------------------
def _normalize_path(path: str) -> str:
    p = (path or "").strip()
    if len(p) > 1 and p.endswith("/"):
        p = p.rstrip("/")
    return p


def _find_matching_endpoint(method: str, path: str, endpoints: list):
    norm_method = (method or "").upper().strip()
    norm_path = _normalize_path(path)

    # 1. Exact match
    for ep in endpoints:
        if ep.method.upper() == norm_method and ep.path == path:
            return ep

    # 2. Normalized trailing slash match
    for ep in endpoints:
        if ep.method.upper() == norm_method and _normalize_path(ep.path) == norm_path:
            return ep

    # 3. Path template matching ({id} vs {user_id} or raw values)
    for ep in endpoints:
        if ep.method.upper() != norm_method:
            continue
        ep_norm = _normalize_path(ep.path)
        pattern = "^" + re.sub(r"\{[^}]+\}", r"[^/]+", ep_norm) + "$"
        target_eval = re.sub(r"\{[^}]+\}", "placeholder", norm_path)
        if re.match(pattern, target_eval) or re.match(pattern, norm_path):
            return ep

    return None


# ---------------------------------------------------------
# TASK 1: GENERATE PIPELINE (AI Phase)
# ---------------------------------------------------------
async def generate_pipeline_task(ctx, spec_id: int):
    print(f"[WORKER] Generating Smart Pipeline for Spec ID: {spec_id}")
    async with AsyncSessionLocal() as db:
        # Eagerly load endpoints and qa_ir_snapshot to avoid MissingGreenlet error
        stmt = (
            select(APISpecification)
            .options(
                selectinload(APISpecification.endpoints),
                selectinload(APISpecification.qa_ir_snapshot),
            )
            .filter(APISpecification.id == spec_id)
        )
        result = await db.execute(stmt)
        spec = result.scalar_one_or_none()

        if not spec:
            return {"status": "failed", "error": "Spec not found"}

        try:
            if not spec.endpoints:
                return {"status": "failed", "error": "Specification has no parsed endpoints"}

            qa_ir = build_qa_ir(spec.endpoints, spec.version)
            if spec.qa_ir_snapshot:
                spec.qa_ir_snapshot.fingerprint, spec.qa_ir_snapshot.document = (
                    qa_ir["fingerprint"],
                    qa_ir,
                )
            else:
                db.add(
                    QAIRSnapshot(
                        specification_id=spec.id,
                        fingerprint=qa_ir["fingerprint"],
                        document=qa_ir,
                    )
                )

            coverage = plan_coverage(qa_ir)
            db.add(
                CoveragePlan(
                    specification_id=spec.id,
                    fingerprint=qa_ir["fingerprint"],
                    plan=coverage,
                )
            )

            by_resource = {}
            for endpoint in qa_ir["endpoints"]:
                by_resource.setdefault(endpoint["resource"], []).append(endpoint)

            ai_gen = get_ai_generator()
            ai_scenarios = []
            for resource, endpoints in by_resource.items():
                relevant_intents = [
                    item
                    for item in coverage["selected_intents"]
                    if item["endpoint_id"] in {e["id"] for e in endpoints}
                ]
                compact_context = [
                    {
                        key: endpoint[key]
                        for key in (
                            "path",
                            "method",
                            "summary",
                            "parameters",
                            "request_schema",
                            "responses",
                            "security",
                            "crud",
                            "access",
                            "resource_ids",
                        )
                    }
                    for endpoint in endpoints
                ]
                generated = ai_gen.generate_scenarios(
                    compact_context, intents=relevant_intents, domain=resource
                )
                ai_scenarios.extend(generated)

            # Clear existing scenarios for this spec
            await db.execute(delete(TestScenario).where(TestScenario.specification_id == spec_id))
            await db.commit()

            saved_scenarios_count = 0
            for s_data in ai_scenarios:
                # Match steps against existing endpoints; skip hallucinated calls gracefully
                valid_steps = []
                for step_data in s_data.steps:
                    matched_ep = _find_matching_endpoint(
                        step_data.endpoint_method, step_data.endpoint_path, spec.endpoints
                    )
                    if matched_ep:
                        valid_steps.append((matched_ep, step_data))
                    else:
                        print(
                            f"[WORKER] Skipping step referencing non-existent endpoint: "
                            f"{step_data.endpoint_method} {step_data.endpoint_path}"
                        )

                # Skip saving scenario if it has no valid steps
                if not valid_steps:
                    continue

                new_scenario = TestScenario(
                    specification_id=spec_id,
                    name=s_data.name,
                    description=s_data.description,
                )
                db.add(new_scenario)
                await db.flush()

                for i, (matched_ep, step_data) in enumerate(valid_steps):
                    new_step = ScenarioStep(
                        scenario_id=new_scenario.id,
                        endpoint_id=matched_ep.id,
                        step_type=step_data.step_type,
                        category=step_data.category,
                        mutates_state=step_data.mutates_state,
                        step_order=i + 1,
                        payload=step_data.payload,
                        path_params=step_data.path_params,
                        query_params=step_data.query_params,
                        extract_rules=[r.model_dump() for r in (step_data.extract_rules or [])],
                        inject_rules=[r.model_dump() for r in (step_data.inject_rules or [])],
                        expected_status=step_data.expected_status,
                    )
                    db.add(new_step)

                saved_scenarios_count += 1

            await db.commit()
            return {
                "status": "completed",
                "message": "Pipelines generated successfully",
                "scenarios": saved_scenarios_count,
                "domains": len(by_resource),
            }

        except Exception as e:
            await db.rollback()
            return {"status": "failed", "error": str(e)}


# ---------------------------------------------------------
# TASK 2: EXECUTE PIPELINE (LangGraph Phase)
# ---------------------------------------------------------
async def run_pipeline_task(
    ctx,
    pipeline_id: int,
    base_url: str,
    test_identity_id: int | None = None,
    verify_tls: bool = True,
):
    print(f"[WORKER] Executing Pipeline ID: {pipeline_id}")
    async with AsyncSessionLocal() as db:
        stmt = (
            select(TestScenario)
            .options(selectinload(TestScenario.steps).selectinload(ScenarioStep.endpoint))
            .filter(TestScenario.id == pipeline_id)
        )
        result = await db.execute(stmt)
        scenario = result.scalar_one_or_none()

        if not scenario:
            return {"status": "failed", "error": "Pipeline not found"}

        auth_session = None
        if test_identity_id:
            stmt = (
                select(TestIdentity)
                .options(selectinload(TestIdentity.auth_profile))
                .join(AuthProfile)
                .filter(TestIdentity.id == test_identity_id)
            )
            result = await db.execute(stmt)
            identity = result.scalar_one_or_none()
            if not identity:
                return {"status": "failed", "error": "Test identity not found"}
            try:
                auth_session = build_auth_session(identity.auth_profile, identity, base_url)
                import httpx

                async with httpx.AsyncClient(
                    timeout=15.0, follow_redirects=False, verify=verify_tls
                ) as auth_client:
                    await auth_session.authenticate(auth_client)
            except AuthenticationError as exc:
                return {"status": "failed", "error": f"Authentication failed: {exc}"}

        scenario.steps.sort(key=lambda x: x.step_order)
        current_timestamp = str(int(time.time()))

        steps_for_graph = []
        for step in scenario.steps:
            payload = step.payload
            if payload and isinstance(payload, dict):
                payload_str = json.dumps(payload).replace("{{TIMESTAMP}}", current_timestamp)
                payload = json.loads(payload_str)

            steps_for_graph.append(
                {
                    "id": step.id,
                    "step_type": step.step_type,
                    "mutates_state": step.mutates_state,
                    "endpoint_method": step.endpoint.method,
                    "endpoint_path": step.endpoint.path,
                    "payload": payload,
                    "query_params": step.query_params,
                    "extract_rules": step.extract_rules,
                    "inject_rules": step.inject_rules,
                    "expected_status": step.expected_status,
                    "step_order": step.step_order,
                }
            )

        # INIT STATE
        initial_state = {
            "pipeline_id": pipeline_id,
            "steps": steps_for_graph,
            "memory": {},
            "results": [],
            "setup_failed": False,
            "cleanup_warnings": [],
            "base_url": base_url,
            "verify_tls": verify_tls,
            "auth_session": auth_session,
        }

        # RUN LANGGRAPH
        final_state = await unified_pipeline_app.ainvoke(initial_state)

        # SAVE RESULTS TO DB (Batch Commit)
        await db.execute(
            delete(TestResult).where(
                TestResult.scenario_step_id.in_([s["id"] for s in steps_for_graph])
            )
        )

        for res in final_state["results"]:
            db.add(
                TestResult(
                    scenario_step_id=res["scenario_step_id"],
                    actual_status=res["actual_status"],
                    is_passed=res["is_passed"],
                    response_body=res["response_body"],
                    execution_time_ms=res["execution_time_ms"],
                    error_message=res["error_message"],
                    failure_classification=res.get("failure_classification"),
                    request_metadata=res.get("request_metadata"),
                    response_metadata=res.get("response_metadata"),
                )
            )
        await db.commit()

        return {
            "status": "completed",
            "setup_failed": final_state["setup_failed"],
            "cleanup_warnings": final_state["cleanup_warnings"],
            "total_executed": len(final_state["results"]),
            "passed": sum(1 for r in final_state["results"] if r["is_passed"]),
        }


async def run_all_pipelines_task(
    ctx,
    spec_id: int,
    base_url: str,
    test_identity_id: int | None = None,
    verify_tls: bool = True,
):
    """Execute every generated scenario for a specification sequentially.

    Sequential orchestration deliberately prevents one scenario's test data or
    authentication refresh from interfering with another scenario's cleanup.
    Safe requests inside each scenario remain parallelised by the graph.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TestScenario.id)
            .where(TestScenario.specification_id == spec_id)
            .order_by(TestScenario.id)
        )
        pipeline_ids = list(result.scalars())
    if not pipeline_ids:
        return {"status": "failed", "error": "No generated pipelines found"}

    outcomes = []
    for pipeline_id in pipeline_ids:
        outcome = await run_pipeline_task(ctx, pipeline_id, base_url, test_identity_id, verify_tls)
        outcomes.append({"pipeline_id": pipeline_id, **outcome})
    completed = [item for item in outcomes if item["status"] == "completed"]
    return {
        "status": "completed",
        "pipelines_total": len(outcomes),
        "pipelines_completed": len(completed),
        "pipelines_failed": len(outcomes) - len(completed),
        "total_executed": sum(item.get("total_executed", 0) for item in completed),
        "passed": sum(item.get("passed", 0) for item in completed),
        "cleanup_warnings": [warning for item in completed for warning in item.get("cleanup_warnings", [])],
        "outcomes": outcomes,
    }


class WorkerSettings:
    functions = [generate_pipeline_task, run_pipeline_task, run_all_pipelines_task]
    redis_settings = RedisSettings(host="127.0.0.1", port=6379)
    job_timeout = 900  # 15 minutes allowed for heavy pipelines

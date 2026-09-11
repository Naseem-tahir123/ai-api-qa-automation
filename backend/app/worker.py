from arq.connections import RedisSettings
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import delete

from app.db.database import AsyncSessionLocal
from app.models.specification import APISpecification
from app.models.scenario import TestScenario, ScenarioStep
from app.models.test_result import TestResult
from app.models.auth_profile import AuthProfile, TestIdentity
from app.services.ai_generator import get_ai_generator
from app.services.auth_runtime import AuthenticationError, build_auth_session
from app.services.workflow_executor import unified_pipeline_app
import time
import json

# ---------------------------------------------------------
# TASK 1: GENERATE PIPELINE (AI Phase)
# ---------------------------------------------------------
async def generate_pipeline_task(ctx, spec_id: int):
    print(f"[WORKER] Generating Smart Pipeline for Spec ID: {spec_id}")
    async with AsyncSessionLocal() as db:
        stmt = select(APISpecification).options(selectinload(APISpecification.endpoints)).filter(APISpecification.id == spec_id)
        result = await db.execute(stmt)
        spec = result.scalar_one_or_none()

        if not spec: return {"status": "failed", "error": "Spec not found"}

        endpoints_info = [{"path": e.path, "method": e.method, "summary": e.summary, "parameters": e.parameters, "request_schema": e.request_schema, "response_schema": e.response_schema} for e in spec.endpoints]

        ai_gen = get_ai_generator()
        try:
            ai_scenarios = ai_gen.generate_scenarios(endpoints_info)
            
            # Clear old scenarios for this spec
            await db.execute(delete(TestScenario).where(TestScenario.specification_id == spec_id))
            await db.commit()

            for s_data in ai_scenarios:
                new_scenario = TestScenario(specification_id=spec_id, name=s_data.name, description=s_data.description)
                db.add(new_scenario)
                await db.flush()

                for i, step_data in enumerate(s_data.steps):
                    matched_endpoint = next((e for e in spec.endpoints if e.path == step_data.endpoint_path and e.method == step_data.endpoint_method), None)
                    ep_id = matched_endpoint.id if matched_endpoint else spec.endpoints[0].id

                    new_step = ScenarioStep(
                        scenario_id=new_scenario.id,
                        endpoint_id=ep_id,
                        step_type=step_data.step_type,
                        category=step_data.category,
                        mutates_state=step_data.mutates_state,
                        step_order=i + 1,
                        payload=step_data.payload,
                        path_params=step_data.path_params,
                        query_params=step_data.query_params,
                        extract_rules=[r.model_dump() for r in (step_data.extract_rules or [])],
                        inject_rules=[r.model_dump() for r in (step_data.inject_rules or [])],
                        expected_status=step_data.expected_status
                    )
                    db.add(new_step)
            await db.commit()
            return {"status": "completed", "message": "Pipeline generated successfully"}
        except Exception as e:
            await db.rollback()
            return {"status": "failed", "error": str(e)}

# ---------------------------------------------------------
# TASK 2: EXECUTE PIPELINE (LangGraph Phase)
# ---------------------------------------------------------
async def run_pipeline_task(ctx, pipeline_id: int, base_url: str, test_identity_id: int | None = None, verify_tls: bool = True):
    print(f"[WORKER] Executing Pipeline ID: {pipeline_id}")
    async with AsyncSessionLocal() as db:
        stmt = select(TestScenario).options(selectinload(TestScenario.steps).selectinload(ScenarioStep.endpoint)).filter(TestScenario.id == pipeline_id)
        result = await db.execute(stmt)
        scenario = result.scalar_one_or_none()

        if not scenario: return {"status": "failed", "error": "Pipeline not found"}

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
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=False, verify=verify_tls) as auth_client:
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

            steps_for_graph.append({
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
                "step_order": step.step_order
            })

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
        await db.execute(delete(TestResult).where(TestResult.scenario_step_id.in_([s["id"] for s in steps_for_graph])))
        
        for res in final_state["results"]:
            db.add(TestResult(
                scenario_step_id=res["scenario_step_id"],
                actual_status=res["actual_status"],
                is_passed=res["is_passed"],
                response_body=res["response_body"],
                execution_time_ms=res["execution_time_ms"],
                error_message=res["error_message"]
            ))
        await db.commit()

        return {
            "status": "completed",
            "setup_failed": final_state["setup_failed"],
            "cleanup_warnings": final_state["cleanup_warnings"],
            "total_executed": len(final_state["results"]),
            "passed": sum(1 for r in final_state["results"] if r["is_passed"])
        }

class WorkerSettings:
    functions = [generate_pipeline_task, run_pipeline_task]
    redis_settings = RedisSettings(host="127.0.0.1", port=6379)
    job_timeout = 900  # 15 minutes allowed for heavy pipelines

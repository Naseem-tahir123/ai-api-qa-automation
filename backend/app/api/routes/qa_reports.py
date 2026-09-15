"""Actionable phase-7 dashboard data built from persisted scenario evidence."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.specification import APISpecification
from app.models.scenario import TestScenario, ScenarioStep

router = APIRouter(prefix="/api/v1/qa", tags=["QA Reporting"], dependencies=[Depends(get_current_user)])

@router.get("/specifications/{spec_id}/dashboard")
async def dashboard(spec_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APISpecification).options(selectinload(APISpecification.endpoints), selectinload(APISpecification.qa_ir_snapshot), selectinload(APISpecification.coverage_plans)).where(APISpecification.id == spec_id))
    spec = result.scalar_one_or_none()
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")
    result = await db.execute(select(TestScenario).options(selectinload(TestScenario.steps).selectinload(ScenarioStep.results), selectinload(TestScenario.steps).selectinload(ScenarioStep.endpoint)).where(TestScenario.specification_id == spec_id))
    scenarios = result.scalars().unique().all()
    latest = [step.results[-1] for scenario in scenarios for step in scenario.steps if step.results]
    failures = [item for item in latest if not item.is_passed]
    tested_endpoint_ids = {step.endpoint_id for scenario in scenarios for step in scenario.steps if step.results}
    endpoint_coverage = []
    for endpoint in spec.endpoints:
        endpoint_results = [step.results[-1] for scenario in scenarios for step in scenario.steps if step.endpoint_id == endpoint.id and step.results]
        endpoint_coverage.append({
            "endpoint_id": endpoint.id,
            "endpoint": f"{endpoint.method} {endpoint.path}",
            "executed_steps": len(endpoint_results),
            "passed": sum(result.is_passed for result in endpoint_results),
            "failed": sum(not result.is_passed for result in endpoint_results),
            "status": "executed" if endpoint_results else "not_executed",
        })
    by_failure = {}
    for item in failures:
        key = item.failure_classification or "unknown"
        by_failure[key] = by_failure.get(key, 0) + 1
    plan = spec.coverage_plans[-1].plan if spec.coverage_plans else None
    all_test_evidence = []
    for scenario in scenarios:
        for step in scenario.steps:
            if step.results:
                res = step.results[-1]
                all_test_evidence.append({
                    "scenario_name": scenario.name,
                    "method": step.endpoint.method,
                    "path": step.endpoint.path,
                    "is_passed": res.is_passed,
                    "payload": step.payload,
                    "expected_status": step.expected_status,
                    "actual_status": res.actual_status,
                    "response_body": res.response_body,
                    "error_message": res.error_message,
                    "execution_time_ms": res.execution_time_ms
                })
    actionable_failures = [item for item in all_test_evidence if not item["is_passed"]]
    return {
        "specification_id": spec_id,
        "qa_ir_fingerprint": spec.qa_ir_snapshot.fingerprint if spec.qa_ir_snapshot else None,
        "coverage": {"endpoints_total": len(spec.endpoints), "endpoints_executed": len(tested_endpoint_ids), "percentage": round(100 * len(tested_endpoint_ids) / len(spec.endpoints), 2) if spec.endpoints else 0, "planned_intents": len(plan["selected_intents"]) if plan else 0},
        "execution": {"total": len(latest), "passed": len(latest) - len(failures), "failed": len(failures), "failure_classes": by_failure, "failed_cleanup": sum(1 for scenario in scenarios for step in scenario.steps if step.step_type == "teardown" and step.results and not step.results[-1].is_passed)},
        "pipelines": {"total": len(scenarios), "executed": sum(any(step.results for step in scenario.steps) for scenario in scenarios)},
        "endpoint_coverage": endpoint_coverage,
        "release_risk": "high" if any(item.failure_classification in {"server_error", "authentication_failure"} for item in failures) else "medium" if failures else "low",
        "all_test_evidence": all_test_evidence,
        "actionable_failures": actionable_failures
    }

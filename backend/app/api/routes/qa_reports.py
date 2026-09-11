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
    by_failure = {}
    for item in failures:
        key = item.failure_classification or "unknown"
        by_failure[key] = by_failure.get(key, 0) + 1
    plan = spec.coverage_plans[-1].plan if spec.coverage_plans else None
    return {
        "specification_id": spec_id,
        "qa_ir_fingerprint": spec.qa_ir_snapshot.fingerprint if spec.qa_ir_snapshot else None,
        "coverage": {"endpoints_total": len(spec.endpoints), "endpoints_executed": len(tested_endpoint_ids), "percentage": round(100 * len(tested_endpoint_ids) / len(spec.endpoints), 2) if spec.endpoints else 0, "planned_intents": len(plan["selected_intents"]) if plan else 0},
        "execution": {"total": len(latest), "passed": len(latest) - len(failures), "failed": len(failures), "failure_classes": by_failure, "failed_cleanup": sum(1 for scenario in scenarios for step in scenario.steps if step.step_type == "teardown" and step.results and not step.results[-1].is_passed)},
        "release_risk": "high" if any(item.failure_classification in {"server_error", "authentication_failure"} for item in failures) else "medium" if failures else "low",
    }

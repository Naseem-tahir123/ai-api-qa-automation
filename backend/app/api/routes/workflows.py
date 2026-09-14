from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.security import validate_target_url
from app.db.database import get_db
from app.models.endpoint import Endpoint
from app.models.specification import APISpecification
from app.models.workflow import WorkflowPlan, WorkflowRun, WorkflowStep
from app.schemas.workflow import (
    WorkflowExecutionRequest,
    WorkflowPlanResponse,
    WorkflowReportResponse,
    WorkflowRunResponse,
)
from app.services.workflow_executor import WorkflowExecutor
from app.services.workflow_planner import WorkflowPlanner

router = APIRouter(
    prefix="/api/v1/workflows",
    tags=["Workflow Testing"],
    dependencies=[Depends(get_current_user)],
)


def _plan_options():
    return selectinload(WorkflowPlan.steps).selectinload(WorkflowStep.endpoint).selectinload(Endpoint.test_cases)


async def _get_plan(plan_id: int, db: AsyncSession) -> WorkflowPlan:
    result = await db.execute(select(WorkflowPlan).options(_plan_options()).where(WorkflowPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Workflow plan not found")
    return plan


@router.post("/specifications/{specification_id}/plans", response_model=WorkflowPlanResponse, status_code=201)
async def generate_plan(specification_id: int, db: AsyncSession = Depends(get_db)):
    spec = (await db.execute(select(APISpecification).where(APISpecification.id == specification_id))).scalar_one_or_none()
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")

    endpoints = list((await db.execute(select(Endpoint).where(Endpoint.specification_id == specification_id))).scalars().all())
    if not endpoints:
        raise HTTPException(status_code=400, detail="The specification has no endpoints")

    definitions, graph = WorkflowPlanner.build(endpoints)
    plan = WorkflowPlan(
        specification_id=specification_id,
        name=f"{spec.filename} workflow",
        status="ready",
        graph=graph,
    )
    db.add(plan)
    await db.flush()

    steps = []
    for position, definition in enumerate(definitions, start=1):
        step = WorkflowStep(
            plan_id=plan.id,
            endpoint_id=definition.endpoint.id,
            position=position,
            name=definition.endpoint.summary or f"{definition.endpoint.method.upper()} {definition.endpoint.path}",
            depends_on=[],
            capture_rules=definition.capture_rules,
            injection_rules=definition.injection_rules,
            is_cleanup=definition.is_cleanup,
        )
        db.add(step)
        steps.append((step, definition))
    await db.flush()

    endpoint_to_step = {step.endpoint_id: step.id for step, _ in steps}
    for step, definition in steps:
        step.depends_on = [endpoint_to_step[item] for item in definition.depends_on_endpoint_ids if item in endpoint_to_step]

    await db.commit()
    return await _get_plan(plan.id, db)


@router.get("/specifications/{specification_id}/plans", response_model=list[WorkflowPlanResponse])
async def list_plans(specification_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkflowPlan).options(_plan_options()).where(WorkflowPlan.specification_id == specification_id).order_by(WorkflowPlan.created_at.desc())
    )
    return list(result.scalars().unique().all())


@router.get("/plans/{plan_id}", response_model=WorkflowPlanResponse)
async def get_plan(plan_id: int, db: AsyncSession = Depends(get_db)):
    return await _get_plan(plan_id, db)


@router.post("/plans/{plan_id}/execute", response_model=WorkflowRunResponse)
async def execute_plan(plan_id: int, request: WorkflowExecutionRequest, db: AsyncSession = Depends(get_db)):
    try:
        target_base_url = validate_target_url(request.target_base_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Security blocked this URL: {exc}") from exc
    plan = await _get_plan(plan_id, db)
    if any(not step.endpoint.test_cases for step in plan.steps):
        missing = [step.endpoint_id for step in plan.steps if not step.endpoint.test_cases]
        raise HTTPException(status_code=400, detail={"message": "Generate test cases before workflow execution", "endpoint_ids": missing})
    return await WorkflowExecutor.execute(
        plan, target_base_url, request.auth_config, request.stop_on_failure, request.run_cleanup, db
    )


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)):
    run = (await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run


@router.get("/plans/{plan_id}/report", response_model=WorkflowReportResponse)
async def get_latest_report(plan_id: int, db: AsyncSession = Depends(get_db)):
    plan = await _get_plan(plan_id, db)
    run = (await db.execute(
        select(WorkflowRun).where(WorkflowRun.plan_id == plan_id).order_by(WorkflowRun.started_at.desc()).limit(1)
    )).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="No workflow run exists for this plan")

    root_causes = [
        {"step_id": item.get("step_id"), "endpoint_id": item.get("endpoint_id"), "reason": item.get("reason")}
        for item in run.step_results
        if item.get("status") == "failed"
    ]
    recommendations = []
    if root_causes:
        recommendations.append("Fix the earliest failed producer before retesting dependent endpoints.")
    if any(item.get("status") == "blocked" for item in run.step_results):
        recommendations.append("Review blocked steps after upstream failures are resolved; they were not independently evaluated.")
    if not root_causes:
        recommendations.append("Workflow dependencies and expected HTTP statuses completed successfully.")

    return WorkflowReportResponse(
        plan_id=plan.id,
        run_id=run.id,
        workflow_status=run.status,
        summary=run.summary,
        dependency_graph=plan.graph,
        runtime_context=run.runtime_context,
        step_results=run.step_results,
        root_causes=root_causes,
        recommendations=recommendations,
    )

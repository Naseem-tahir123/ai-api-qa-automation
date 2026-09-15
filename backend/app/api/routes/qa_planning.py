"""QA-IR, deterministic coverage, and specification-change APIs."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.qa_artifacts import CoveragePlan, QAIRSnapshot
from app.models.specification import APISpecification
from app.services.coverage_planner import plan_coverage
from app.services.qa_ir import build_qa_ir, diff_qa_ir

router = APIRouter(prefix="/api/v1/qa", tags=["QA Planning"], dependencies=[Depends(get_current_user)])


async def _spec(db: AsyncSession, spec_id: int) -> APISpecification:
    result = await db.execute(select(APISpecification).options(selectinload(APISpecification.endpoints), selectinload(APISpecification.qa_ir_snapshot)).where(APISpecification.id == spec_id))
    spec = result.scalar_one_or_none()
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")
    return spec


@router.post("/specifications/{spec_id}/ir")
async def build_ir(spec_id: int, db: AsyncSession = Depends(get_db)):
    spec = await _spec(db, spec_id)
    if not spec.endpoints:
        raise HTTPException(status_code=409, detail="Parse the specification before building QA-IR.")
    document = build_qa_ir(spec.endpoints, spec.version)
    snapshot = spec.qa_ir_snapshot
    if snapshot:
        snapshot.fingerprint, snapshot.document = document["fingerprint"], document
    else:
        snapshot = QAIRSnapshot(specification_id=spec.id, fingerprint=document["fingerprint"], document=document)
        db.add(snapshot)
    await db.commit()
    return document


@router.get("/specifications/{spec_id}/ir")
async def get_ir(spec_id: int, db: AsyncSession = Depends(get_db)):
    spec = await _spec(db, spec_id)
    if not spec.qa_ir_snapshot:
        raise HTTPException(status_code=404, detail="QA-IR has not been built.")
    return spec.qa_ir_snapshot.document


@router.post("/specifications/{spec_id}/coverage-plan")
async def create_coverage_plan(spec_id: int, db: AsyncSession = Depends(get_db)):
    spec = await _spec(db, spec_id)
    if not spec.qa_ir_snapshot:
        raise HTTPException(status_code=409, detail="Build QA-IR before creating a coverage plan.")
    plan = plan_coverage(spec.qa_ir_snapshot.document)
    db.add(CoveragePlan(specification_id=spec.id, fingerprint=spec.qa_ir_snapshot.fingerprint, plan=plan))
    await db.commit()
    return plan


@router.get("/specifications/{spec_id}/coverage-plan")
async def get_coverage_plan(spec_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CoveragePlan).where(CoveragePlan.specification_id == spec_id).order_by(CoveragePlan.created_at.desc()))
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Coverage plan has not been created.")
    return plan.plan


@router.get("/specifications/{spec_id}/regression-impact")
async def regression_impact(spec_id: int, db: AsyncSession = Depends(get_db)):
    spec = await _spec(db, spec_id)
    if not spec.qa_ir_snapshot:
        raise HTTPException(status_code=409, detail="Build QA-IR before calculating regression impact.")
    result = await db.execute(select(QAIRSnapshot).join(APISpecification).where(APISpecification.project_id == spec.project_id, QAIRSnapshot.specification_id != spec.id).order_by(QAIRSnapshot.created_at.desc()))
    previous = result.scalars().first()
    changes = diff_qa_ir(previous.document if previous else None, spec.qa_ir_snapshot.document)
    impacted = sorted(set(changes["added"] + changes["changed"]))
    return {"baseline_specification_id": previous.specification_id if previous else None, "changes": changes,
            "impacted_endpoints": impacted, "recommendation": "Run scenarios linked to impacted endpoints."}

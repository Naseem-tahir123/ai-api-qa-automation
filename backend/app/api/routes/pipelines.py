from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional

from app.db.database import get_db
from app.models.specification import APISpecification
from app.models.scenario import TestScenario, ScenarioStep
from app.models.environment import ProjectEnvironment
from app.models.auth_profile import AuthProfile, TestIdentity
from app.api.deps import get_current_user
from app.core.security import validate_target_url
from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job

router = APIRouter(prefix="/api/v1/pipelines", tags=["Unified Smart Pipelines"], dependencies=[Depends(get_current_user)])

async def get_redis_pool():
    return await create_pool(RedisSettings(host="127.0.0.1", port=6379))

class PipelineExecutionRequest(BaseModel):
    target_base_url: Optional[str] = None
    environment_id: Optional[int] = None
    test_identity_id: Optional[int] = None
    allow_production: bool = False
    allow_destructive: bool = False
    
    @field_validator("target_base_url")
    @classmethod
    def prevent_ssrf(cls, v: str) -> str:
        if v is None:
            return v
        try:
            return validate_target_url(v)
        except ValueError as e:
            raise ValueError(f"Security blocked this URL: {str(e)}") 

    @model_validator(mode="after")
    def require_execution_target(self):
        if bool(self.target_base_url) == bool(self.environment_id):
            raise ValueError("Provide exactly one of target_base_url or environment_id.")
        if self.test_identity_id and not self.environment_id:
            raise ValueError("test_identity_id requires environment_id.")
        return self

# 1. GENERATE PIPELINE (AI Phase)
@router.post("/generate/{spec_id}", status_code=202)
async def generate_pipeline(spec_id: int, db: AsyncSession = Depends(get_db), redis = Depends(get_redis_pool)):
    result = await db.execute(select(APISpecification).filter(APISpecification.id == spec_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Specification not found")

    job = await redis.enqueue_job("generate_pipeline_task", spec_id)
    return {"message": "Pipeline generation started.", "task_id": job.job_id, "status": "queued"}

# 2. RUN PIPELINE (Execution Phase)
@router.post("/run/{pipeline_id}", status_code=202)
async def run_pipeline(
    pipeline_id: int,
    request: PipelineExecutionRequest,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis_pool),
):
    scenario_result = await db.execute(select(TestScenario).options(selectinload(TestScenario.steps).selectinload(ScenarioStep.endpoint)).where(TestScenario.id == pipeline_id))
    safety_scenario = scenario_result.scalar_one_or_none()
    if not safety_scenario:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    has_destructive_step = any(step.endpoint.method.upper() == "DELETE" for step in safety_scenario.steps)
    if has_destructive_step and not request.allow_destructive:
        raise HTTPException(status_code=403, detail="This pipeline has destructive steps. Set allow_destructive=true after approving the target environment.")
    target_base_url = request.target_base_url
    verify_tls = True

    if request.environment_id:
        result = await db.execute(
            select(TestScenario.specification_id).filter(TestScenario.id == pipeline_id)
        )
        specification_id = result.scalar_one_or_none()
        if specification_id is None:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        result = await db.execute(
            select(ProjectEnvironment)
            .join(APISpecification, ProjectEnvironment.project_id == APISpecification.project_id)
            .filter(
                ProjectEnvironment.id == request.environment_id,
                APISpecification.id == specification_id,
            )
        )
        environment = result.scalar_one_or_none()
        if not environment:
            raise HTTPException(status_code=404, detail="Environment not found for this pipeline's project")
        if environment.is_production and not request.allow_production:
            raise HTTPException(
                status_code=403,
                detail="Production execution requires allow_production=true.",
            )
        target_base_url = environment.base_url
        verify_tls = environment.verify_tls

        if request.test_identity_id:
            result = await db.execute(
                select(TestIdentity)
                .join(AuthProfile, TestIdentity.auth_profile_id == AuthProfile.id)
                .filter(
                    TestIdentity.id == request.test_identity_id,
                    AuthProfile.environment_id == environment.id,
                )
            )
            if not result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="Test identity not found for this environment")

    job = await redis.enqueue_job(
        "run_pipeline_task", pipeline_id, target_base_url, request.test_identity_id, verify_tls
    )
    return {"message": "Pipeline execution started.", "task_id": job.job_id, "status": "queued"}

# 3. CHECK TASK STATUS
@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, redis = Depends(get_redis_pool)):
    job = Job(task_id, redis)
    try:
        info = await job.info()
        status = await job.status()
        if status.value == "complete":
            return {"task_id": task_id, "status": "completed", "result": await job.result()}
        return {"task_id": task_id, "status": status.value}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Task not found: {str(e)}")

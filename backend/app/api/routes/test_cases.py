import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.orm import selectinload
from typing import List

from app.db.database import get_db
from app.models.endpoint import Endpoint
from app.models.specification import APISpecification
from app.models.test_case import TestCase
from app.schemas.test_case import TestCaseResponse
from app.services.ai_generator import AITestGenerator, get_ai_generator
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/test-cases", tags=["Test Cases"], dependencies=[Depends(get_current_user)])


async def get_redis_pool():
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
    return await create_pool(RedisSettings(host="127.0.0.1", port=6379))

@router.post("/generate/{endpoint_id}", response_model=List[TestCaseResponse])
async def generate_tests_for_endpoint(
    endpoint_id: int,
    db: AsyncSession = Depends(get_db),
    ai_gen: AITestGenerator = Depends(get_ai_generator)
):
    # 1. Retrieve the endpoint from the database for which test cases need to be generated
    result = await db.execute(select(Endpoint).filter(Endpoint.id == endpoint_id))
    endpoint = result.scalar_one_or_none()

    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    # 2. Send the endpoint data to the AI generator
    try:
        ai_test_cases = ai_gen.generate_test_cases(
            method=endpoint.method,
            path=endpoint.path,
            request_schema=endpoint.request_schema or {},
            response_schema=endpoint.response_schema or {},
            parameters=endpoint.parameters or []
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Generation Failed: {str(e)}")

    # Audit report fix: Remove existing test cases first to avoid duplication
    await db.execute(delete(TestCase).where(TestCase.endpoint_id == endpoint_id))

    # 3. Save the AI-generated test cases to the database
    saved_test_cases = []
    for tc in ai_test_cases:
        new_tc = TestCase(
            endpoint_id=endpoint_id,
            category=tc.category,
            description=tc.description,
            payload=tc.payload,
            path_params=tc.path_params,
            query_params=tc.query_params,
            expected_status=tc.expected_status
        )
        db.add(new_tc)
        saved_test_cases.append(new_tc)

    await db.commit()

    # Refresh the objects to retrieve generated IDs
    for tc in saved_test_cases:
        await db.refresh(tc)

    return saved_test_cases

@router.post("/generate-all/{spec_id}", status_code=202)
async def generate_all_tests_for_spec(
    spec_id: int,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis_pool) 
):
    
    result = await db.execute(select(APISpecification).filter(APISpecification.id == spec_id) )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Specification not found")
    job = await redis.enqueue_job("generate_tests_task", spec_id)

    if not job:
        raise HTTPException(status_code=500, detail="Failed to enqueue job for test generation")
    return {
        "message": "Test generation started in background.",
        "task_id": job.job_id,
        "spec_id": spec_id,
        "status": "queued"
    }

 

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, redis = Depends(get_redis_pool)):
    job = Job(task_id, redis)
    
    try:
        info = await job.info()
        status = await job.status()
        
        # Agar job completely done hai
        if status.value == "complete":
            result = await job.result()
            return {"task_id": task_id, "status": "completed", "result": result}
            
        return {
            "task_id": task_id, 
            "status": status.value,  # 'queued', 'in_progress' etc.
            "enqueue_time": info.enqueue_time if info else None
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Task not found: {str(e)}")
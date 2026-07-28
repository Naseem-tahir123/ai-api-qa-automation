from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.endpoint import Endpoint
from app.schemas.test_result import ExecutionSummary
from app.services.executor import TestExecutionEngine

router = APIRouter(prefix="/api/v1/execution", tags=["Test Execution"])

@router.post("/run/{endpoint_id}", response_model=ExecutionSummary)
async def execute_tests(
    endpoint_id: int, 
    target_base_url: str = Query(..., description="Target Server Base URL (e.g. https://httpbin.org)"),
    db: AsyncSession = Depends(get_db)
):
    # 1. Endpoint aur uske test cases database se selectinload se fetch karein
    stmt = select(Endpoint).options(selectinload(Endpoint.test_cases)).filter(Endpoint.id == endpoint_id)
    result = await db.execute(stmt)
    endpoint = result.scalar_one_or_none()
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
        
    if not endpoint.test_cases:
        raise HTTPException(status_code=400, detail="No test cases found. Please generate test cases first.")

    # 2. Execution Engine chalayein
    results = await TestExecutionEngine.run_tests_for_endpoint(
        endpoint=endpoint,
        test_cases=endpoint.test_cases,
        target_base_url=target_base_url,
        db=db
    )
    
    # 3. Pass aur Fail ki ginti karein
    passed_count = sum(1 for r in results if r.is_passed)
    failed_count = len(results) - passed_count
    
    return ExecutionSummary(
        endpoint_id=endpoint_id,
        total_executed=len(results),
        passed=passed_count,
        failed=failed_count,
        results=results
    )
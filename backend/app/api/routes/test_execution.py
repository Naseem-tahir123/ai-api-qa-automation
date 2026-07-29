from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.endpoint import Endpoint
from app.schemas.test_result import ExecutionSummary
from app.services.executor import TestExecutionEngine
from app.models.specification import APISpecification

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



@router.post("/run-all/{spec_id}")
async def execute_all_tests_for_spec(
    spec_id: int, 
    target_base_url: str = Query(..., description="Target Server Base URL (e.g. https://httpbin.org)"),
    db: AsyncSession = Depends(get_db)
):
    # 1. Spec check karein
    spec_result = await db.execute(select(APISpecification).filter(APISpecification.id == spec_id))
    spec = spec_result.scalar_one_or_none()
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")

    # 2. Spec ke tamam Endpoints aur unke test cases fetch karein
    stmt = select(Endpoint).options(selectinload(Endpoint.test_cases)).filter(Endpoint.specification_id == spec_id)
    endpoints_result = await db.execute(stmt)
    endpoints = endpoints_result.scalars().all()

    if not endpoints:
        raise HTTPException(status_code=400, detail="No endpoints found for this specification.")

    total_executed = 0
    total_passed = 0
    total_failed = 0
    
    # 3. Har endpoint par loop lagayen aur TestEngine chalayen
    for ep in endpoints:
        if ep.test_cases:  # Agar is endpoint ke tests generate hue hain toh run karein
            results = await TestExecutionEngine.run_tests_for_endpoint(
                endpoint=ep,
                test_cases=ep.test_cases,
                target_base_url=target_base_url,
                db=db
            )
            
            passed_count = sum(1 for r in results if r.is_passed)
            total_passed += passed_count
            total_failed += (len(results) - passed_count)
            total_executed += len(results)

    return {
        "message": f"Bulk execution completed for Spec ID: {spec_id}",
        "total_endpoints_processed": len(endpoints),
        "total_tests_executed": total_executed,
        "total_passed": total_passed,
        "total_failed": total_failed
    }
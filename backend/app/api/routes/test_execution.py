from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.endpoint import Endpoint
from app.schemas.test_result import ExecutionSummary
from app.services.executor import TestExecutionEngine
from app.models.specification import APISpecification
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/execution", tags=["Test Execution"], dependencies=[Depends(get_current_user)])

class ExecutionRequest(BaseModel):
    target_base_url: str
    auth_config: Optional[Dict[str, str]] = {
        "token": "YourBearerTokenHere",
        "api_key": "YourAPIKeyHere"
    }  # e.g., {"token": "eyJhbG..."}

@router.post("/run/{endpoint_id}", response_model=ExecutionSummary)
async def execute_tests(
    endpoint_id: int, 
    request: ExecutionRequest,
    db: AsyncSession = Depends(get_db)
):
    # Fetch the endpoint and its test cases in a single eager-loading query.
    stmt = select(Endpoint).options(selectinload(Endpoint.test_cases)).filter(Endpoint.id == endpoint_id)
    result = await db.execute(stmt)
    endpoint = result.scalar_one_or_none()
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
        
    if not endpoint.test_cases:
        raise HTTPException(status_code=400, detail="No test cases found. Please generate test cases first.")

    # Execute the endpoint's saved test cases.
    results = await TestExecutionEngine.run_tests_for_endpoint(
        endpoint=endpoint,
        test_cases=endpoint.test_cases,
        target_base_url=request.target_base_url,
        auth_config=request.auth_config,
        db=db
    )
    
    # Calculate pass and fail totals.
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
    request: ExecutionRequest,
    db: AsyncSession = Depends(get_db)
):
    # Verify that the specification exists.
    spec_result = await db.execute(select(APISpecification).filter(APISpecification.id == spec_id))
    spec = spec_result.scalar_one_or_none()
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")

    # Fetch all specification endpoints and their test cases.
    stmt = select(Endpoint).options(selectinload(Endpoint.test_cases)).filter(Endpoint.specification_id == spec_id)
    endpoints_result = await db.execute(stmt)
    endpoints = endpoints_result.scalars().all()

    if not endpoints:
        raise HTTPException(status_code=400, detail="No endpoints found for this specification.")

    total_executed = 0
    total_passed = 0
    total_failed = 0
    
    # Execute saved test cases for each endpoint.
    for ep in endpoints:
        if ep.test_cases:  # Execute only endpoints with generated test cases.
            results = await TestExecutionEngine.run_tests_for_endpoint(
                endpoint=ep,
                test_cases=ep.test_cases,
                target_base_url=request.target_base_url,
                auth_config=request.auth_config,
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

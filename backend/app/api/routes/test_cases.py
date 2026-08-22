from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
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

@router.post("/generate-all/{spec_id}")
async def generate_all_tests_for_spec(
    spec_id: int,
    db: AsyncSession = Depends(get_db),
    ai_gen: AITestGenerator = Depends(get_ai_generator)
):
    # 1. Fetch the specification along with all its associated endpoints
    stmt = (
        select(APISpecification)
        .options(selectinload(APISpecification.endpoints))
        .filter(APISpecification.id == spec_id)
    )
    result = await db.execute(stmt)
    spec = result.scalar_one_or_none()

    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")

    total_generated = 0
    endpoints_processed = 0
    failed_endpoints = 0

    # 2. Iterate through each endpoint and generate test cases using AI
    for endpoint in spec.endpoints:

        # Audit report fix: Remove existing test cases first to avoid duplication
        await db.execute(delete(TestCase).filter(TestCase.endpoint_id == endpoint.id))
        await db.execute(delete(TestCase).where(TestCase.endpoint_id == endpoint.id))
        await db.commit()

        try:
            # Send endpoint data to the AI generator
            ai_test_cases = ai_gen.generate_test_cases(
                method=endpoint.method,
                path=endpoint.path,
                request_schema=endpoint.request_schema or {},
                response_schema=endpoint.response_schema or {},
                parameters=endpoint.parameters
            )

            # Save generated test cases to the database
            for tc in ai_test_cases:
                new_tc = TestCase(
                    endpoint_id=endpoint.id,
                    category=tc.category,
                    description=tc.description,
                    payload=tc.payload,
                    path_params=tc.path_params,
                    query_params=tc.query_params,
                    expected_status=tc.expected_status
                )
                db.add(new_tc)
                total_generated += 1

            endpoints_processed += 1

            # Commit after each endpoint so progress is not lost if a failure occurs later
            await db.commit()

        except Exception as e:
            # If AI generation fails for one endpoint, continue processing the remaining endpoints
            print(f"Failed to generate tests for endpoint {endpoint.path}: {str(e)}")
            failed_endpoints += 1

            # Roll back the transaction to prevent partial data from being saved
            await db.rollback()

    return {
        "message": f"Bulk test generation completed for Spec ID: {spec_id}",
        "total_endpoints_processed": endpoints_processed,
        "endpoints_successfully_processed": endpoints_processed,
        "endpoints_failed": failed_endpoints,
        "total_tests_generated": total_generated
    }
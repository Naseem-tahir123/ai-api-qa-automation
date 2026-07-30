from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.database import get_db
from app.models.endpoint import Endpoint
from app.models.test_case import TestCase
from app.schemas.test_case import TestCaseResponse
from app.services.ai_generator import AITestGenerator, get_ai_generator

router = APIRouter(prefix="/api/v1/test-cases", tags=["Test Cases"])
@router.post("/generate/{endpoint_id}", response_model=List[TestCaseResponse])
async def generate_tests_for_endpoint(endpoint_id: int, db: AsyncSession = Depends(get_db), ai_gen: AITestGenerator = Depends(get_ai_generator)):
    # 1. Database se Endpoint nikalein (Jiske test cases bananey hain)
    result = await db.execute(select(Endpoint).filter(Endpoint.id == endpoint_id))
    endpoint = result.scalar_one_or_none()
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    # 2. AI ko Endpoint ka data bhejein
    try:
        ai_test_cases = ai_gen.generate_test_cases(
            method=endpoint.method,
            path=endpoint.path,
            request_schema=endpoint.request_schema,
            response_schema=endpoint.response_schema
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Generation Failed: {str(e)}")

    # 3. AI ke banaye test cases ko Database mein save karein
    saved_test_cases = []
    for tc in ai_test_cases:
        new_tc = TestCase(
            endpoint_id=endpoint_id,
            category=tc.category,
            description=tc.description,
            payload=tc.payload,
            expected_status=tc.expected_status
        )
        db.add(new_tc)
        saved_test_cases.append(new_tc)
        
    await db.commit()
    
    # Refresh taake IDs mil jayein
    for tc in saved_test_cases:
        await db.refresh(tc)
        
    return saved_test_cases
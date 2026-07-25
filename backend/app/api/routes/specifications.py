from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.database import get_db
from app.models.specification import APISpecification
from app.models.endpoint import Endpoint
from app.schemas.specification import EndpointResponse
from app.services.parser import OpenAPIParser

router = APIRouter(prefix="/api/v1/specifications", tags=["Specifications"])

@router.post("/{spec_id}/parse", response_model=List[EndpointResponse])
async def parse_specification(spec_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Check karein ke specification exist karti hai ya nahi
    result = await db.execute(select(APISpecification).filter(APISpecification.id == spec_id))
    spec = result.scalar_one_or_none()
    
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")

    try:
        # 2. File ko parse karein using Parser Service
        parsed_endpoints = OpenAPIParser.parse_spec(spec.file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    # 3. Purane endpoints (agar koi thay) delete kar dein taake duplicate na hon
    delete_stmt = select(Endpoint).filter(Endpoint.specification_id == spec_id)
    old_endpoints = await db.execute(delete_stmt)
    for old_ep in old_endpoints.scalars().all():
        await db.delete(old_ep)
    
    # 4. Naye endpoints ko Database mein add karein
    new_db_endpoints = []
    for ep_data in parsed_endpoints:
        new_ep = Endpoint(
            specification_id=spec_id,
            path=ep_data["path"],
            method=ep_data["method"],
            summary=ep_data["summary"],
            request_schema=ep_data["request_schema"],
            response_schema=ep_data["response_schema"]
        )
        db.add(new_ep)
        new_db_endpoints.append(new_ep)
        
    await db.commit()
    
    # 5. Saved endpoints wapis return karein
    return new_db_endpoints
from arq import Worker
from arq.connections import RedisSettings
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import delete

from app.db.database import AsyncSessionLocal
from app.models.specification import APISpecification
from app.models.test_case import TestCase
from app.services.ai_generator import get_ai_generator


async def generate_tests_task(ctx, spec_id: int):
    """
    Background job that runs outside FastAPI to prevent blocking the server.
    """
    print(f"[WORKER] Starting test generation for Spec ID: {spec_id}")

    # Create a separate database session for the worker.
    async with AsyncSessionLocal() as db:
        stmt = (
            select(APISpecification)
            .options(selectinload(APISpecification.endpoints))
            .filter(APISpecification.id == spec_id)
        )
        result = await db.execute(stmt)
        spec = result.scalar_one_or_none()

        if not spec:
            return {"status": "failed", "error": "Specification not found"}

        ai_gen = get_ai_generator()
        total_generated = 0
        failed_endpoints = 0

        for endpoint in spec.endpoints:
            print(f"[WORKER] Processing endpoint: {endpoint.path}")

            # Remove existing test cases before generating new ones.
            await db.execute(delete(TestCase).where(TestCase.endpoint_id == endpoint.id))
            await db.commit()

            try:
                ai_test_cases = ai_gen.generate_test_cases(
                    method=endpoint.method,
                    path=endpoint.path,
                    request_schema=endpoint.request_schema or {},
                    response_schema=endpoint.response_schema or {},
                    parameters=endpoint.parameters
                )

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

                await db.commit()

            except Exception as e:
                print(f"[WORKER] Failed endpoint {endpoint.path}: {str(e)}")
                failed_endpoints += 1
                await db.rollback()

    print(f"[WORKER] Finished! Generated {total_generated} tests.")

    return {
        "spec_id": spec_id,
        "total_generated": total_generated,
        "failed_endpoints": failed_endpoints,
        "status": "completed"
    }


# Arq settings used by the worker process.
class WorkerSettings:
    functions = [generate_tests_task]

    # Update the host or port here if Redis is running elsewhere.
    redis_settings =  RedisSettings(host="127.0.0.1", port=6379)
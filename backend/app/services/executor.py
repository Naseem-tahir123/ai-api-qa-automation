import time
import httpx
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.endpoint import Endpoint
from app.models.test_case import TestCase
from app.models.test_result import TestResult

class TestExecutionEngine:
    @staticmethod
    async def run_tests_for_endpoint(
        endpoint: Endpoint, 
        test_cases: List[TestCase], 
        target_base_url: str, 
        db: AsyncSession
    ) -> List[TestResult]:
        
        # Base URL formatting (Slashes remove karna)
        base_url = target_base_url.rstrip("/")
        full_url = f"{base_url}{endpoint.path}"
        
        results = []
        
        # Async HTTP Client create karna
        async with httpx.AsyncClient(timeout=10.0) as client:
            for tc in test_cases:
                start_time = time.time()
                actual_status = None
                response_data = None
                error_msg = None
                is_passed = False
                
                try:
                    # Target API par Real Request bhejna
                    response = await client.request(
                        method=endpoint.method,
                        url=full_url,
                        json=tc.payload if tc.payload else None
                    )
                    
                    execution_time = (time.time() - start_time) * 1000  # Milliseconds
                    actual_status = response.status_code
                    
                    # Response JSON parse karna
                    try:
                        response_data = response.json()
                    except Exception:
                        response_data = {"raw_text": response.text[:500]}
                        
                    # PASS/FAIL Check Logic
                    is_passed = (actual_status == tc.expected_status)
                    
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000
                    error_msg = str(e)
                    is_passed = False
                    
                # DB Result Record create karna
                result_record = TestResult(
                    test_case_id=tc.id,
                    actual_status=actual_status,
                    is_passed=is_passed,
                    response_body=response_data,
                    execution_time_ms=round(execution_time, 2),
                    error_message=error_msg
                )
                
                db.add(result_record)
                results.append(result_record)
                
        await db.commit()
        
        for r in results:
            await db.refresh(r)
            
        return results
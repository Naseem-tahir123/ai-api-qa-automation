# backend/app/services/executor.py

import time
import httpx
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.endpoint import Endpoint
from app.models.test_case import TestCase
from app.models.test_result import TestResult
from langsmith import traceable


 
def get_category_priority(category: str) -> int:
    """
    Dynamically decides the priority of a test case based on keyword matching.
    Ensures Happy Paths run first, and Error/Edge cases run last.
    """
    cat_lower = category.lower() if category else ""
    
    # 1. Happy Path & Success states (Must run FIRST)
    # Covers: "Positive / Happy Path", "Positive", "Successful registration..."
    if any(word in cat_lower for word in ["positive", "happy", "success", "retrieve", "get"]):
        return 0
        
    # 2. Negative, Error, Duplicate, and Edge/Boundary cases (Must run LAST)
    # Covers: "Error Handling", "Negative Testing", "Edge Cases", "Invalid Data Types"
    if any(word in cat_lower for word in ["negative", "error", "edge", "boundary", "duplicate", "invalid"]):
        return 3
        
    # 3. Auth, Security and Access controls
    # Covers: "Authentication & Authorization", "Security Validation"
    if any(word in cat_lower for word in ["security", "auth", "permission"]):
        return 2
        
    # 4. Standard schema/field validations
    # Covers: "Required Field Validation", "Optional Field Validation", "Business Logic Validation"
    if any(word in cat_lower for word in ["validation", "type", "field", "required", "optional"]):
        return 1
        
    return 4  # Default fallback for any unknown categories
# =========================================================================


class TestExecutionEngine:
    @traceable(name="run_tests_for_endpoint")
    @staticmethod
    async def run_tests_for_endpoint(
        endpoint: Endpoint,
        test_cases: List[TestCase],
        target_base_url: str,
        auth_config: dict,  
        db: AsyncSession
    ) -> List[TestResult]:

        base_url = target_base_url.rstrip("/")
        results = []

        # Sort the test cases dynamically using our smart substring matching helper
        sorted_test_cases = sorted(
            test_cases,
            key=lambda tc: get_category_priority(tc.category)
        )

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            for tc in sorted_test_cases:  # Loop runs on dynamically sorted list
                start_time = time.time()

                # 1. Replace path parameter placeholders
                formatted_path = endpoint.path
                if tc.path_params:
                    for key, value in tc.path_params.items():
                        formatted_path = formatted_path.replace(f"{{{key}}}", str(value))

                full_url = f"{base_url}{formatted_path}"

                # 2. Dynamically inject authentication headers
                headers = {}
                if endpoint.security:
                    for sec_req in endpoint.security:
                        sec_keys = str(sec_req).lower()
                        if "bearer" in sec_keys and auth_config.get("token"):
                            headers["Authorization"] = f"Bearer {auth_config['token']}"
                        elif "apikey" in sec_keys and auth_config.get("api_key"):
                            headers["x-api-key"] = auth_config["api_key"]

                try:
                    # 3. Send the actual HTTP request
                    response = await client.request(
                        method=endpoint.method,
                        url=full_url,
                        json=tc.payload if tc.payload else None,
                        params=tc.query_params if tc.query_params else None,
                        headers=headers if headers else None
                    )

                    execution_time = (time.time() - start_time) * 1000
                    actual_status = response.status_code

                    try:
                        response_data = response.json()
                    except Exception:
                        response_data = {"raw_text": response.text[:500]}

                    is_passed = (actual_status == tc.expected_status)
                    error_msg = None

                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000
                    actual_status = None
                    response_data = None
                    error_msg = f"Request Failed: {str(e)}"
                    is_passed = False

                # Save the execution result to the database
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
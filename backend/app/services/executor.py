import time
import httpx
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.endpoint import Endpoint
from app.models.test_case import TestCase
from app.models.test_result import TestResult
from langsmith import traceable


class TestExecutionEngine:
    @traceable(name="run_tests_for_endpoint")
    @staticmethod
    async def run_tests_for_endpoint(
        endpoint: Endpoint,
        test_cases: List[TestCase],
        target_base_url: str,
        auth_config: dict,  # <-- NEW: Receive authentication credentials from the user
        db: AsyncSession
    ) -> List[TestResult]:

        base_url = target_base_url.rstrip("/")
        results = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            for tc in test_cases:
                start_time = time.time()

                # 1. Replace path parameter placeholders (e.g., /users/{uuid} -> /users/123)
                formatted_path = endpoint.path
                if tc.path_params:
                    for key, value in tc.path_params.items():
                        formatted_path = formatted_path.replace(f"{{{key}}}", str(value))

                full_url = f"{base_url}{formatted_path}"

                # 2. Dynamically inject authentication headers
                headers = {}
                if endpoint.security:
                    # Security definitions are typically represented as a list of dictionaries
                    # Example: [{"HTTPBearer": []}]
                    for sec_req in endpoint.security:
                        sec_keys = str(sec_req).lower()

                        # Add a Bearer token if required by the API and provided by the user
                        if "bearer" in sec_keys and auth_config.get("token"):
                            headers["Authorization"] = f"Bearer {auth_config['token']}"

                        # Add an API key if required by the API and provided by the user
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
                        # Store the raw response text if the response is not valid JSON
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

        # Refresh all records to load database-generated values (e.g., IDs, timestamps)
        for r in results:
            await db.refresh(r)

        return results
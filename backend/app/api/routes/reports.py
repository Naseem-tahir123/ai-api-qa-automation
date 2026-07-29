from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.specification import APISpecification
from app.models.endpoint import Endpoint
from app.models.test_case import TestCase
from app.models.test_result import TestResult
from app.schemas.report import ProjectQA_Report, EndpointSummary, FailureDetail

router = APIRouter(prefix="/api/v1/reports", tags=["Reports Dashboard"])

@router.get("/specifications/{spec_id}", response_model=ProjectQA_Report)
async def generate_qa_report(spec_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Fetch Complete Data Hierarchy (Spec -> Endpoints -> Cases -> Results)
    stmt = select(APISpecification).options(
        selectinload(APISpecification.endpoints)
        .selectinload(Endpoint.test_cases)
        .selectinload(TestCase.results)
    ).filter(APISpecification.id == spec_id)
    
    result = await db.execute(stmt)
    spec = result.scalar_one_or_none()

    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")

    # 2. Expert QA Metrics Initialization
    total_endpoints = len(spec.endpoints)
    tested_endpoints = 0
    total_tests_run = 0
    total_passed = 0
    total_failed = 0
    total_time_ms = 0.0
    
    category_metrics = {
        "Positive": {"passed": 0, "failed": 0},
        "Negative": {"passed": 0, "failed": 0},
        "Boundary": {"passed": 0, "failed": 0},
        "Other": {"passed": 0, "failed": 0}
    }
    
    endpoint_summaries = []
    actionable_failures = []

    # 3. Deep Data Processing Loop
    for ep in spec.endpoints:
        ep_total_tests = 0
        ep_passed = 0
        ep_failed = 0
        ep_time_ms = 0.0
        
        has_run = False
        
        for tc in ep.test_cases:
            if tc.results:
                has_run = True
                latest_result = tc.results[-1] # Aakhri baar ka result
                
                ep_total_tests += 1
                total_time_ms += (latest_result.execution_time_ms or 0)
                ep_time_ms += (latest_result.execution_time_ms or 0)
                
                # Category tracker
                cat = tc.category if tc.category in category_metrics else "Other"
                
                if latest_result.is_passed:
                    ep_passed += 1
                    category_metrics[cat]["passed"] += 1
                else:
                    ep_failed += 1
                    category_metrics[cat]["failed"] += 1
                    
                    # Capture Failure Details (Bug Report)
                    actionable_failures.append(
                        FailureDetail(
                            endpoint_path=ep.path,
                            method=ep.method,
                            test_category=tc.category,
                            description=tc.description,
                            payload_sent=tc.payload,
                            expected_status=tc.expected_status,
                            actual_status=latest_result.actual_status,
                            error_message=latest_result.error_message
                        )
                    )

        if has_run:
            tested_endpoints += 1
            total_tests_run += ep_total_tests
            total_passed += ep_passed
            total_failed += ep_failed
            
            avg_time = round(ep_time_ms / ep_total_tests, 2) if ep_total_tests > 0 else 0.0
            
            endpoint_summaries.append(
                EndpointSummary(
                    endpoint_id=ep.id,
                    path=ep.path,
                    method=ep.method,
                    total_tests=ep_total_tests,
                    passed=ep_passed,
                    failed=ep_failed,
                    avg_execution_time_ms=avg_time
                )
            )

    # 4. Final Percentage Calculations
    coverage = (tested_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0.0
    pass_rate = (total_passed / total_tests_run * 100) if total_tests_run > 0 else 0.0

    return ProjectQA_Report(
        project_id=spec.project_id,
        spec_id=spec.id,
        total_endpoints_in_spec=total_endpoints,
        tested_endpoints=tested_endpoints,
        coverage_percentage=round(coverage, 2),
        total_tests_executed=total_tests_run,
        total_passed=total_passed,
        total_failed=total_failed,
        pass_rate_percentage=round(pass_rate, 2),
        total_execution_time_ms=round(total_time_ms, 2),
        category_breakdown=category_metrics,
        endpoint_details=endpoint_summaries,
        actionable_failures=actionable_failures
    )
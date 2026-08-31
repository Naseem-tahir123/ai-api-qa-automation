from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List

from app.db.database import get_db
from app.models.specification import APISpecification
from app.models.scenario import TestScenario, ScenarioStep
from app.services.ai_generator import AITestGenerator, get_ai_generator
from app.services.workflow_executor import scenario_executor_app  # LangGraph App
from app.api.deps import get_current_user
from app.api.routes.test_execution import ExecutionRequest  # Reuse same execution schema
import time

router = APIRouter(prefix="/api/v1/scenarios", tags=["Stateful Scenarios"], dependencies=[Depends(get_current_user)])

# =========================================================================
# 1. GENERATE SCENARIOS (AI Phase)
# =========================================================================
@router.post("/generate/{spec_id}")
async def generate_scenarios_for_spec(
    spec_id: int,
    db: AsyncSession = Depends(get_db),
    ai_gen: AITestGenerator = Depends(get_ai_generator)
):
    # Fetch the specification and all its endpoints
    stmt = select(APISpecification).options(selectinload(APISpecification.endpoints)).filter(APISpecification.id == spec_id)
    result = await db.execute(stmt)
    spec = result.scalar_one_or_none()

    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found")

    # Prepare summary data for the endpoints to send to the AI
    endpoints_info = []
    for ep in spec.endpoints:
        endpoints_info.append({
            "path": ep.path,
            "method": ep.method,
            "summary": ep.summary,
            "parameters": ep.parameters,
            "request_schema": ep.request_schema,
            "response_schema": ep.response_schema
        })

    # Generate scenarios using AI
    try:
        ai_scenarios = ai_gen.generate_scenarios(endpoints_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Scenario Generation Failed: {str(e)}")

    # Save the generated scenarios to the database
    saved_scenarios = []
    for s_data in ai_scenarios:
        new_scenario = TestScenario(
            specification_id=spec_id,
            name=s_data.name,
            description=s_data.description
        )
        db.add(new_scenario)
        await db.flush()  # Flush to get the new_scenario.id

        # Save the steps for each scenario
        for i, step_data in enumerate(s_data.steps):
            # Find the endpoint ID for mapping
            matched_endpoint = next((e for e in spec.endpoints if e.path == step_data.endpoint_path and e.method == step_data.endpoint_method), None)
            ep_id = matched_endpoint.id if matched_endpoint else spec.endpoints[0].id

            new_step = ScenarioStep(
                scenario_id=new_scenario.id,
                endpoint_id=ep_id,
                step_order=i + 1,
                payload=step_data.payload,
                extract_rules=[r.model_dump() for r in (step_data.extract_rules or [])],
                inject_rules=[r.model_dump() for r in (step_data.inject_rules or [])],
                expected_status=step_data.expected_status
            )
            db.add(new_step)
        
        saved_scenarios.append(new_scenario)

    await db.commit()
    return {"message": f"Successfully generated {len(saved_scenarios)} stateful scenarios."}


# =========================================================================
# 2. EXECUTE SCENARIO (LangGraph Phase)
# =========================================================================
@router.post("/run/{scenario_id}")
async def run_stateful_scenario(
    scenario_id: int,
    request: ExecutionRequest,
    db: AsyncSession = Depends(get_db)
):
    # Fetch the scenario and its steps from the database (ordered by step_order)
    stmt = select(TestScenario).options(
        selectinload(TestScenario.steps).selectinload(ScenarioStep.endpoint)
    ).filter(TestScenario.id == scenario_id)
    
    result = await db.execute(stmt)
    scenario = result.scalar_one_or_none()

    if not scenario or not scenario.steps:
        raise HTTPException(status_code=404, detail="Scenario or steps not found")

    # Sort steps strictly to ensure the correct execution order
    scenario.steps.sort(key=lambda x: x.step_order)

    # Build a list of step dictionaries for LangGraph
    steps_for_graph = []
    current_timestamp = str(int(time.time()))  # Generate a unique value for email fields
    
    for step in scenario.steps:
        # Dynamic timestamp injection (Approach 1)
        payload = step.payload
        if payload and isinstance(payload, dict):
            import json
            payload_str = json.dumps(payload).replace("{{TIMESTAMP}}", current_timestamp)
            payload = json.loads(payload_str)

        steps_for_graph.append({
            "method": step.endpoint.method,
            "path": step.endpoint.path,
            "payload": payload,
            "extract_rules": step.extract_rules,
            "inject_rules": step.inject_rules,
            "expected_status": step.expected_status,
            "step_order": step.step_order
        })

    # INITIALIZE LANGGRAPH STATE (The Global Memory)
    initial_state = {
        "scenario_id": scenario_id,
        "steps": steps_for_graph,
        "current_step_index": 0,
        "memory": {},         # Start with empty memory
        "results": [],
        "base_url": request.target_base_url,
        "auth_config": request.auth_config
    }

    # 🌟 RUN LANGGRAPH APP!
    # ainvoke means async invoke - this runs the entire graph until it reaches END
    final_state = await scenario_executor_app.ainvoke(initial_state)

    # Return the execution results and memory context
    return {
        "scenario": scenario.name,
        "final_memory": final_state["memory"],
        "execution_results": final_state["results"]
    }


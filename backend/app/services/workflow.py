from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END
import httpx
from faker import Faker

fake = Faker()

# State define karna jo graph ke nodes ke darmiyan data share karegi
class TestState(TypedDict):
    endpoint_url: str
    endpoint_schema: Dict[str, Any]
    scenarios: List[str]
    payloads: List[Dict[str, Any]]
    results: List[Dict[str, Any]]


# Node 1: Plan Scenarios (Simple AI routing/mock planning)
def plan_scenarios_node(state: TestState):
    # Abhi ke liye hum static scenarios plan kar rahe hain (Positive aur Missing Field)
    scenarios = ["Scenario_1_Positive_Signup", "Scenario_2_Missing_Username"]
    return {"scenarios": scenarios}


# Node 2: Generate Payload (AI logic ke baghair Faker use karna)
def generate_data_node(state: TestState):
    scenarios = state["scenarios"]
    schema_fields = state["endpoint_schema"]
    payloads = []
    
    for scenario in scenarios:
        payload = {}
        if "Positive" in scenario:
            # Sahi data bharna
            for field, f_type in schema_fields.items():
                if f_type == "str" and "email" in field:
                    payload[field] = fake.email()
                elif f_type == "str":
                    payload[field] = fake.user_name()[:10]
                elif f_type == "int":
                    payload[field] = fake.random_int(min=18, max=60)
        else:
            # Negative: Username ko blank chorna
            for field, f_type in schema_fields.items():
                if field == "username" or field == "name":
                    payload[field] = "" # Empty for failure test
                elif f_type == "str" and "email" in field:
                    payload[field] = fake.email()
                elif f_type == "int":
                    payload[field] = fake.random_int(min=18, max=60)
                    
        payloads.append(payload)
        
    return {"payloads": payloads}


# Node 3: Execute Tests using HTTPX
def execute_tests_node(state: TestState):
    payloads = state["payloads"]
    target_url = state["endpoint_url"]
    results = []
    
    # HTTPX client for non-blocking requests
    with httpx.Client() as client:
        for idx, payload in enumerate(payloads):
            try:
                # Real HTTP request bhejna target API par
                response = client.post(target_url, json=payload, timeout=5.0)
                results.append({
                    "test_case": state["scenarios"][idx],
                    "payload_sent": payload,
                    "status_code": response.status_code,
                    "response_received": response.text[:200]  # Pehle 200 characters
                })
            except Exception as e:
                results.append({
                    "test_case": state["scenarios"][idx],
                    "payload_sent": payload,
                    "error": f"Connection Failed: {str(e)}"
                })
                
    return {"results": results}


# Graph compile karna
workflow = StateGraph(TestState)

workflow.add_node("plan_scenarios", plan_scenarios_node)
workflow.add_node("generate_data", generate_data_node)
workflow.add_node("execute_tests", execute_tests_node)

workflow.add_edge(START, "plan_scenarios")
workflow.add_edge("plan_scenarios", "generate_data")
workflow.add_edge("generate_data", "execute_tests")
workflow.add_edge("execute_tests", END)

compiled_workflow = workflow.compile()
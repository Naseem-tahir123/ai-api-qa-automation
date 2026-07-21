from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from app.schema_generator import generate_dynamic_model
from app.workflow import compiled_workflow

app = FastAPI(title="AI API QA Automation Platform - MVP")

# Request class humare trigger endpoint ke liye
class RunTestRequest(BaseModel):
    target_url: str                 # API jisko test karna hai (e.g. https://httpbin.org/post)
    fields_schema: Dict[str, str]   # fields rules (e.g. {"username": "str", "email": "str"})


@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Backend is running flawlessly!"}


@app.post("/api/v1/execute-dynamic-tests")
def execute_tests(request: RunTestRequest):
    try:
        # 1. Dynamic Pydantic Model bana kar validation check karna
        # (MVP mein check karne ke liye ke humara generator sahi chal raha hai)
        DynamicModel = generate_dynamic_model("UserRequestModel", request.fields_schema)
        
        # 2. State prepare karna LangGraph ke liye
        initial_state = {
            "endpoint_url": request.target_url,
            "endpoint_schema": request.fields_schema,
            "scenarios": [],
            "payloads": [],
            "results": []
        }
        
        # 3. LangGraph workflow run karna
        final_state = compiled_workflow.invoke(initial_state)
        
        # 4. Results wapis bhejna (Report)
        return {
            "message": "Tests generated and executed successfully",
            "dynamic_model_name": DynamicModel.__name__,
            "total_test_cases": len(final_state["results"]),
            "report": final_state["results"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution Failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
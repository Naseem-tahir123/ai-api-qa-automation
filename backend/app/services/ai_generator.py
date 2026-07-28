import os
import json # <-- JSON conversion ke liye
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.schemas.test_case import AITestPlan


class AITestGenerator:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.2,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # FIX 1: 'method="json_mode"' lagaya taake OpenAI ka Tool Parser crash na ho
        self.structured_llm = self.llm.with_structured_output(AITestPlan, method="json_mode")

    def generate_test_cases(self, method: str, path: str, request_schema: dict, response_schema: dict):
        
        # FIX 2: Python Dicts ko Valid Double-Quoted JSON Strings mein badla
        req_json_str = json.dumps(request_schema, indent=2) if request_schema else "{}"
        res_json_str = json.dumps(response_schema, indent=2) if response_schema else "{}"

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an Expert API QA Automation Engineer. Your job is to analyze the given API endpoint schema and generate realistic Test Cases (Positive and Negative). You MUST respond in valid JSON."),
            ("human", """
            Please generate 3 test cases (1 Positive, 2 Negative) for the following endpoint:
            
            Method: {method}
            Path: {path}
            
            Request Schema:
            {req_schema_str}
            
            Response Schema:
            {res_schema_str}
            
            IMPORTANT:
            - Make the 'payload' realistic (use real-looking names, emails, etc).
            - Strictly follow the constraints given in the Request Schema.
            - Ensure 'expected_status' matches the Response Schema (e.g., 200 for success, 422 for validation error).
            
            Output a JSON object with a root key "test_cases" containing an array of objects. Each object must have keys: "category", "description", "payload", and "expected_status".
            """)
        ])

        chain = prompt | self.structured_llm
    
        # FIX 3: Dynamic strings pass kiye invoke mein
        result = chain.invoke({
            "method": method,
            "path": path,
            "req_schema_str": req_json_str,
            "res_schema_str": res_json_str
        })

        return result.test_cases
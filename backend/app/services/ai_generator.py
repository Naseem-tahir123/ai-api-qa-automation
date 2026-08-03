import os
import json  # <-- Used to convert Python dictionaries into valid JSON strings
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

        # FIX 1: Use json_mode to prevent OpenAI structured output parsing issues
        self.structured_llm = self.llm.with_structured_output(
            AITestPlan,
            method="json_mode"
        )

    def generate_test_cases(
        self,
        method: str,
        path: str,
        request_schema: dict,
        response_schema: dict,
        parameters: list
    ):

        # FIX 2: Convert Python dictionaries into properly formatted JSON strings
        req_json_str = json.dumps(request_schema, indent=2) if request_schema else "{}"
        res_json_str = json.dumps(response_schema, indent=2) if response_schema else "{}"

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an Expert API QA Automation Engineer. Your job is to analyze the given API endpoint schema and generate realistic Test Cases (Positive and Negative). You MUST respond in valid JSON."
            ),
            (
                "human",
                """
                Please generate 3 test cases (1 Positive, 2 Negative) for the following endpoint:
                
                Method: {method}
                Path: {path}

                Parameters (Path/Query):
                {parameters}
                
                Request Schema:
                {req_schema_str}
                
                Response Schema:
                {res_schema_str}
                
                IMPORTANT:
                1. If the path contains parameters (e.g. /users/{{id}}), generate realistic values in 'path_params'.
                2. If there are required query parameters, include them in 'query_params'.
                3. Put the request body in 'payload'.
                4. Ensure 'expected_status' matches the Response Schema.
                
                Output a JSON object with a root key "test_cases" containing an array of objects. Each object must have keys: "category", "description", "payload", and "expected_status".
                """
            )
        ])

        chain = prompt | self.structured_llm

        # FIX 3: Pass the dynamically generated JSON strings to the prompt
        result = chain.invoke({
            "method": method,
            "path": path,
            "parameters": parameters,
            "req_schema_str": req_json_str,
            "res_schema_str": res_json_str
        })

        return result.test_cases


def get_ai_generator():
    return AITestGenerator()
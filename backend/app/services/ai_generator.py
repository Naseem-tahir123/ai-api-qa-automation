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
        """
        You are a Senior API QA Automation Engineer with expertise in functional, validation, security, and negative testing.

        Your task is to analyze the provided API endpoint specification and generate a comprehensive set of realistic test cases similar to those created by an experienced QA engineer.

        Generate only valid JSON matching the expected schema.
        """
    ),
    (
        "human",
        """
        Analyze the following API endpoint and generate comprehensive test coverage.

        Method: {method}
        Path: {path}

        Parameters (Path/Query):
        {parameters}

        Request Schema:
        {req_schema_str}

        Response Schema:
        {res_schema_str}

        Generate all relevant test cases based on the endpoint definition, including when applicable:

        - Positive / Happy Path
        - Negative Testing
        - Boundary Value Testing
        - Required Field Validation
        - Optional Field Validation
        - Invalid Data Types
        - Missing Parameters
        - Invalid Path Parameters
        - Invalid Query Parameters
        - Authentication & Authorization
        - Security Validation
        - Error Handling
        - Edge Cases
        - Business Logic Validation

        IMPORTANT:
        1. Generate only relevant test cases for the given endpoint.
        2. Do not generate duplicate or redundant test cases.
        3. If the path contains parameters (e.g. /users/{{id}}), generate realistic values in 'path_params'.
        4. If query parameters exist, include them in 'query_params'.
        5. Put request body data in 'payload'.
        6. Include authentication-related test cases when the endpoint requires security.
        7. Generate realistic positive and negative payloads.
        8. Ensure 'expected_status' reflects the expected API behavior.
        9. Create enough test cases to provide meaningful coverage; do not limit yourself to a fixed number.
        10. Think like a QA engineer testing a production API.

        Output a JSON object with a root key "test_cases".

        Each test case must contain:
        - category
        - description
        - payload
        - path_params
        - query_params
        - expected_status
        """
    )
        ])

        chain = prompt | self.structured_llm

        # FIX 3: Pass the dynamically generated JSON strings to the prompt
        result = chain.invoke(
        {
            "method": method,
            "path": path,
            "parameters": parameters,
            "req_schema_str": req_json_str,
            "res_schema_str": res_json_str
        },
        config={
            "run_name": f"Generate Test Cases for {method} {path}",
            "tags": ["test_case_generation", method],
            "metadata":{
                "endpoint_method": method,
                "endpoint_path": path
            },
        },
        )
        return result.test_cases


def get_ai_generator():
    return AITestGenerator()

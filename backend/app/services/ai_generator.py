import os
import json  # <-- Used to convert Python dictionaries into valid JSON strings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.schemas.test_case import AITestPlan
from app.schemas.scenario import AITestScenarioPlan


class AITestGenerator:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.2,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # FIX 1: Use json_mode to prevent OpenAI structured output parsing issues
      

        self.scenario_llm = self.llm.with_structured_output(
            AITestScenarioPlan,
            method = "json_mode"
        )


    def generate_scenarios(self, spec_endpoints_info: list):
        """
        Takes a lish of all endpoints in a spec and generates Unified Smart Pipelines.
        """
        endpoints_json_str = json.dumps(spec_endpoints_info, indent=2)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """
                You are an Elite QA Architect designing a Unified Smart Pipeline for API testing.
                Your task is to analyze API endpoints and build robust, chained Test Scenarios.
                
                Each Scenario MUST follow this 3-Layer Unified Pipeline Architecture:
                1. SETUP (step_type: 'setup'): Create resources or authenticate. Extract IDs/tokens to memory.
                2. TEST (step_type: 'test'): Bombard the created resource with multiple tests. 
                   - Generate Positive, Negative, Boundary, and Edge case tests using the extracted memory.
                   - Set `mutates_state = true` if the test modifies the resource (PUT/PATCH/DELETE).
                   - Set `mutates_state = false` for safe tests (GET or invalid payloads that will be rejected).
                3. TEARDOWN (step_type: 'teardown'): Delete the created resources to clean the database. (If no DELETE endpoint exists, skip teardown gracefully).

                Memory Rules:
                - `extract_rules`: {"json_path": "$.id", "save_as": "doc_id"}
                - `inject_rules`: {"target": "path", "field": "id", "use_memory": "doc_id"}

                Generate ONLY valid JSON matching the schema.
                """
            ),
            (
                "human",
                """
                Analyze the following API endpoints and generate 2 to 3 Unified Smart Pipelines (Scenarios).
                
                API Endpoints:
                {endpoints_data}

                IMPORTANT RULES:
                1. A scenario represents an end-to-end journey (e.g. Auth Flow, Document CRUD).
                2. Use `{{{{TIMESTAMP}}}}` for dynamic fields like email or username in payloads.
                3. Generate at least 5 to 10 'test' steps (Negative, Boundary) in the middle of each scenario.
                4. Always assign the correct `step_type` ('setup', 'test', or 'teardown').
                5. Make sure variables saved in `extract_rules` precisely match the `use_memory` in `inject_rules`.
                6. Do NOT put hardcoded IDs in path_params; use `inject_rules` instead.
                
                Output a JSON object with a root key "scenarios" containing the list of pipelines.
                """
            )
        ])

        chain = prompt | self.scenario_llm

        result = chain.invoke(
            {"endpoints_data": endpoints_json_str},
            config={
                "run_name": "Generate Unified Pipelines",
                "tags": ["pipeline_generation"],
            },
        )
        return result.scenarios
    
    


def get_ai_generator():
    return AITestGenerator()

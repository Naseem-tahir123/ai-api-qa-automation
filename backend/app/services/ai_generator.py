import os
import json  # <-- Used to convert Python dictionaries into valid JSON strings
# from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
# from app.schemas.test_case import AITestPlan
from app.schemas.scenario import AITestScenarioPlan


def _inline_json_schema(schema: dict) -> dict:
    definitions = schema.get("$defs", {})

    def resolve(value):
        if isinstance(value, dict):
            reference = value.get("$ref")
            if reference:
                return resolve(definitions[reference.rsplit("/", 1)[-1]])
            return {
                key: resolve(item)
                for key, item in value.items()
                if key not in {"$defs", "$ref"}
            }
        if isinstance(value, list):
            return [resolve(item) for item in value]
        return value

    return resolve(schema)


class AITestGenerator:
    def __init__(self):
        # OpenAI configuration kept here as a reference while development uses Gemini.
        # self.llm = ChatOpenAI(
        #     model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        #     temperature=0.2,
        #     api_key=os.getenv("OPENAI_API_KEY"),
        #     max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "2")),
        # )
        self.llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            temperature=0.2,
            google_api_key=os.getenv("GEMINI_API_KEY"),
            max_retries=int(os.getenv("GEMINI_MAX_RETRIES", "2")),
            # client_options={"api_version": "v1beta"}
        )

        self.scenario_llm = self.llm.bind(
            response_mime_type="application/json",
            response_schema=_inline_json_schema(AITestScenarioPlan.model_json_schema()),
        )


    def generate_scenarios(self, spec_endpoints_info: list, intents: list | None = None, domain: str = "API"):
        """
        Takes a list of all endpoints in a spec and generates Unified Smart Pipelines.
        """
        endpoints_json_str = json.dumps(spec_endpoints_info, indent=2)
        intents_json_str = json.dumps(intents or [], indent=2)

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
                - `extract_rules`: {{"json_path": "$.id", "save_as": "doc_id"}}
                - `inject_rules`: {{"target": "path", "field": "id", "use_memory": "doc_id"}}

                Generate ONLY valid JSON matching the schema.
                """
            ),
            (
                "human",
                """
                Analyze the following API endpoints for the {domain} domain and generate 1 to 3 Unified Smart Pipelines (Scenarios).
                
                API Endpoints:
                {endpoints_data}

                Required deterministic test intents (cover each applicable intent):
                {test_intents}

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

        try:
            response = chain.invoke(
                {"endpoints_data": endpoints_json_str, "test_intents": intents_json_str, "domain": domain},
                config={
                    "run_name": "Generate Unified Pipelines",
                    "tags": ["pipeline_generation"],
                },
            )
            content = response.content
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            result = AITestScenarioPlan.model_validate(json.loads(content))
        except Exception as exc:
            message = str(exc)
            normalized = message.lower()
            if any(
                marker in normalized
                for marker in ("insufficient_quota", "billing_hard_limit", "exceeded your current quota")
            ):
                raise RuntimeError(
                    "Gemini quota is exhausted. Check the API key usage limits or configure "
                    "a different GEMINI_API_KEY before generating the pipeline."
                ) from exc
            if "429" in normalized or "rate_limit" in normalized:
                raise RuntimeError(
                    "Gemini rate limit persisted after retries. Wait and retry the job, or reduce "
                    "pipeline generation concurrency."
                ) from exc
            raise
        return result.scenarios
    
    


def get_ai_generator():
    return AITestGenerator()

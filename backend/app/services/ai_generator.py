import time
import logging
import random
import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from app.schemas.scenario import AITestScenarioPlan

logger = logging.getLogger(__name__)

_TRANSIENT_ERRORS = ("503", "unavailable", "overloaded", "500", "internal error", "timeout", "deadline")
_QUOTA_ERRORS = ("resource_exhausted", "quota", "429", "insufficient_quota")


def _is_transient(exc: Exception) -> bool:
    text = str(exc).lower()
    if any(marker in text for marker in _QUOTA_ERRORS):
        # Quota khatam ho chuki — isi model par retry karne se faida nahi.
        return False
    return any(marker in text for marker in _TRANSIENT_ERRORS)


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
        self.scenario_schema = _inline_json_schema(AITestScenarioPlan.model_json_schema())
        self._cached_gemini_llms = {}
        self._cached_groq_llms = {}

        # Fallback chain: upar se neeche try hota hai.
        # Pehle Gemini ke generous (Lite) models, phir agar sab fail hon to Groq.
        self._provider_chain = [
            ("gemini", "gemini-3.5-flash-lite"),
            ("gemini", "gemini-2.5-flash-lite"),
            ("groq", "llama-3.3-70b-versatile"),
        ]

    # -------------------- Gemini --------------------
    def _get_gemini_llm(self, model_name: str):
        if model_name not in self._cached_gemini_llms:
            base_llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.2,
                google_api_key=os.getenv("GEMINI_API_KEY"),
                max_retries=0,
            )
            self._cached_gemini_llms[model_name] = base_llm.bind(
                response_mime_type="application/json",
                response_schema=self.scenario_schema,
            )
        return self._cached_gemini_llms[model_name]

    def _invoke_gemini(self, model_name: str, prompt_value) -> AITestScenarioPlan:
        llm = self._get_gemini_llm(model_name)
        response = llm.invoke(prompt_value)
        content = response.content
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        return AITestScenarioPlan.model_validate(json.loads(content))

    # -------------------- Groq --------------------
    def _get_groq_llm(self, model_name: str):
        if model_name not in self._cached_groq_llms:
            base_llm = ChatGroq(
                model=model_name,
                temperature=0.2,
                api_key=os.getenv("GROQ_API_KEY"),
                max_retries=0,
            )
            self._cached_groq_llms[model_name] = base_llm.with_structured_output(
                AITestScenarioPlan, method="function_calling"
            )
        return self._cached_groq_llms[model_name]

    def _invoke_groq(self, model_name: str, prompt_value) -> AITestScenarioPlan:
        llm = self._get_groq_llm(model_name)
        # with_structured_output seedha parsed AITestScenarioPlan object deta hai.
        return llm.invoke(prompt_value)

    # -------------------- Unified retry + fallback --------------------
    def _invoke_with_retry_and_fallback(self, prompt_value) -> AITestScenarioPlan:
        MAX_TRIES_PER_PROVIDER = 3
        last_error = None

        for provider_type, model_name in self._provider_chain:
            invoke_fn = self._invoke_gemini if provider_type == "gemini" else self._invoke_groq

            for attempt in range(MAX_TRIES_PER_PROVIDER):
                try:
                    logger.info(f"Trying {provider_type}:{model_name}, attempt={attempt + 1}")
                    return invoke_fn(model_name, prompt_value)
                except Exception as exc:
                    last_error = exc

                    if not _is_transient(exc):
                        logger.warning(
                            f"{provider_type}:{model_name} permanent error, "
                            f"moving to next provider: {exc}"
                        )
                        break  # is provider ko chhor kar agle par jao

                    wait_seconds = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"{provider_type}:{model_name} busy (attempt {attempt + 1}/"
                        f"{MAX_TRIES_PER_PROVIDER}), waiting {wait_seconds:.1f}s: {exc}"
                    )
                    time.sleep(wait_seconds)
            else:
                # yeh tab chalega jab andar wala loop 'break' na ho, balki saare
                # attempts khatam ho jayein (yani transient errors hi thay)
                logger.warning(f"{provider_type}:{model_name} failed all retries, trying next provider...")
                continue

        raise RuntimeError(f"All providers in fallback chain failed. Last error: {last_error}")

    # -------------------- Public API --------------------
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

        prompt_value = prompt.invoke({
            "endpoints_data": endpoints_json_str,
            "test_intents": intents_json_str,
            "domain": domain,
        })

        try:
            result = self._invoke_with_retry_and_fallback(prompt_value)
        except Exception as exc:
            message = str(exc).lower()
            if any(marker in message for marker in _QUOTA_ERRORS):
                raise RuntimeError(
                    "All configured AI providers hit their quota/rate limits. "
                    "Check GEMINI_API_KEY and GROQ_API_KEY usage limits, or add another provider."
                ) from exc
            raise

        return result.scenarios


def get_ai_generator():
    return AITestGenerator()
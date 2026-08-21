# AI API QA Automation Platform

FastAPI-based backend platform for automated API QA. The system uploads and parses OpenAPI/Swagger specifications, stores discovered endpoints, uses an OpenAI LLM to generate endpoint-level test cases, executes those tests against a target API, and produces QA reporting with pass/fail and coverage metrics.

This README reflects the current codebase implementation. Proposed roadmap items are clearly separated from implemented functionality.

## Current End-to-End Flow

1. A QA project is created through the Projects API.
2. An OpenAPI/Swagger JSON or YAML file is uploaded for that project.
3. The specification parser reads the file, resolves `$ref` references, and extracts endpoint metadata:
   - path
   - HTTP method
   - summary
   - request schema
   - response schema
   - path/query parameters
   - security requirements
4. Parsed endpoints are stored in PostgreSQL.
5. The test generation API sends one endpoint at a time to the LLM.
6. The LLM generates structured test cases such as positive, negative, boundary, validation, auth/security, and edge-case tests.
7. Generated test cases are saved in the database.
8. The execution API runs saved test cases against a user-provided target base URL.
9. The execution engine injects generated request body, path parameters, query parameters, and supported auth headers.
10. Test results are saved with actual status, pass/fail result, response body, execution time, and error details.
11. The reporting API summarizes endpoint coverage, pass rate, failures, and execution metrics.

## Implemented Functionality

| Area | Current Status | Implementation Notes |
| --- | --- | --- |
| Project management | Implemented | Create, list, and retrieve QA projects. |
| Specification upload | Implemented | Upload JSON/YAML API specs and store file metadata. |
| OpenAPI parsing | Implemented | Extracts endpoints, schemas, parameters, and security config. |
| `$ref` resolution | Implemented | Uses `jsonref` to resolve referenced OpenAPI schemas before storing endpoint data. |
| Endpoint storage | Implemented | Parsed endpoints are persisted in PostgreSQL through SQLAlchemy models. |
| LLM test generation | Implemented | Uses OpenAI `gpt-4o-mini` through LangChain structured output. |
| Per-endpoint test generation | Implemented | Generates tests for one selected endpoint. |
| Bulk test generation | Implemented | Iterates through all endpoints in a specification and generates tests sequentially. |
| Test case persistence | Implemented | Stores category, description, payload, path params, query params, and expected status. |
| Test execution | Implemented | Uses HTTPX async client to send real requests to the target API. |
| Path parameter injection | Implemented | Replaces placeholders like `/users/{id}` with generated `path_params`. |
| Query parameter injection | Implemented | Sends generated `query_params` with requests. |
| Authentication injection | Partially implemented | Supports Bearer token and API key header injection when endpoint security metadata is present. |
| Result capture | Implemented | Stores status code, response body, pass/fail, timing, and error message. |
| QA reporting | Implemented | Provides coverage, pass rate, category breakdown, endpoint summaries, and failure details. |

## Current Limitations

The current implementation is endpoint-level and mostly stateless. It can execute generated tests for individual endpoints, but it does not yet manage full business workflows where one request depends on the output of another request.

| Area | Current Status | Remaining Work |
| --- | --- | --- |
| Stateful workflow testing | Not implemented | Add workflow-aware execution across dependent endpoints. |
| Request chaining | Not implemented | Capture values from one response and inject them into later requests. |
| API dependency detection | Not implemented | Detect relationships such as `POST /users` producing an ID for `GET /users/{id}`. |
| Dependency graph | Not implemented | Build a graph showing which endpoints depend on others. |
| Topological execution | Not implemented | Execute independent endpoints in parallel and dependent endpoints in order. |
| Runtime variable store | Not implemented | Add plan-scoped variables for captured IDs/tokens/values. |
| Dependent test generation | Not implemented | Generate valid positive tests using dependency order and placeholders. |
| Test data management | Not implemented | Track data created during test execution. |
| Teardown/cleanup | Not implemented | Delete or clean generated test data after workflow execution. |
| Background jobs | Not implemented | Add queue/worker support for long-running generation and execution. |
| Regression baselines | Not implemented | Store golden responses and compare future runs. |

## Stateful Testing Gap

Current test cases contain static `payload`, `path_params`, and `query_params`. The executor uses those values directly when sending a request. It also stores response bodies in `TestResult`, but those values are only used for reporting.

The current system does not:

- detect that one endpoint depends on another
- capture IDs or values from previous API responses for reuse
- inject captured values into later requests
- maintain an execution context across multiple endpoints
- create workflow-level execution plans
- perform teardown or cleanup for generated data

Example workflow that is not yet fully supported:

```text
Create User -> Get User -> Update User -> Delete User
```

Today, `Get User`, `Update User`, and `Delete User` would need usable IDs already present in generated test cases. If the generated ID does not exist in the target system, positive tests can fail even if the API is working correctly.

## Proposed Stateful Workflow Architecture

To support dependent APIs, the platform should evolve from stateless endpoint execution to plan-based workflow execution:

```text
Dependency Graph
-> Deterministic Dependency Detection
-> LLM-based Field Mapping
-> Placeholder Generation
-> Runtime Value Resolution
-> Execution
-> Teardown/Cleanup
```

Recommended components:

- `ExecutionPlan`: Represents a full workflow test plan for one API specification or scenario.
- `PlanStep`: Represents one executable API call inside the workflow.
- `ExecutionContext`: Runtime store for values captured during execution.
- Runtime variable store: Keeps values such as `user_id`, `order_id`, tokens, or generated resource identifiers.
- Capture rules: Define where values should be extracted from a response.
- Injection rules: Define where captured values should be inserted in later path params, query params, headers, or payloads.
- Teardown steps: Clean up data created during test execution.

Future example:

1. `POST /users` creates a user.
2. Response returns `id = 123`.
3. `ExecutionContext` stores `user.id = 123`.
4. `GET /users/{id}` uses `{id}` from `ExecutionContext`.
5. `PUT /users/{id}` updates the same user.
6. `DELETE /users/{id}` removes test data during cleanup.

## Large and Interconnected API Specs

For large APIs, workflow execution should be driven by dependency order:

- Independent endpoints can run in parallel.
- Dependent endpoints should run sequentially.
- Multiple independent dependency chains can run at the same time.
- Test generation should happen in dependency-aware order so positive cases use valid upstream data.

Example:

```text
Level 1: POST /users, GET /health, GET /categories
Level 2: GET /users/{id}, POST /orders
Level 3: PUT /users/{id}, GET /orders/{id}
Level 4: DELETE /orders/{id}, DELETE /users/{id}
```

This model keeps execution efficient while still respecting real API relationships.

## API Modules

| Module | Role |
| --- | --- |
| `app/api/routes/projects.py` | Project CRUD and specification upload. |
| `app/api/routes/specifications.py` | Parse uploaded specs into endpoints. |
| `app/api/routes/test_cases.py` | Generate AI test cases for one endpoint or all endpoints in a spec. |
| `app/api/routes/test_execution.py` | Execute generated tests against a target API. |
| `app/api/routes/reports.py` | Generate QA dashboard/report data. |
| `app/services/parser.py` | Parse OpenAPI files and extract endpoint metadata. |
| `app/services/ai_generator.py` | Generate structured test cases using OpenAI/LangChain. |
| `app/services/executor.py` | Execute HTTP requests and save test results. |
| `app/models/*` | SQLAlchemy database models. |
| `app/schemas/*` | Pydantic request/response schemas. |

## Technology Stack

| Component | Technology |
| --- | --- |
| Backend framework | FastAPI |
| Language | Python 3.11+ |
| Database | PostgreSQL |
| ORM | SQLAlchemy Async |
| Migrations | Alembic |
| HTTP execution | HTTPX |
| LLM integration | OpenAI `gpt-4o-mini` via LangChain |
| Observability hooks | LangSmith tracing decorators |
| Dependency management | `uv` |

Note: `langgraph` is present in dependencies, but the current workflow planner/state graph functionality is not implemented in the codebase yet.

## Setup

1. Navigate to the backend directory:

```bash
cd ai-api-qa-automation/backend
```

2. Create a `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ai_qa_db
OPENAI_API_KEY=sk-your-key-here
```

3. Install dependencies:

```bash
uv sync
```

4. Run database migrations:

```bash
uv run alembic upgrade head
```

5. Start the API:

```bash
uv run uvicorn main:app --reload
```

6. Health check:

```bash
GET /health
```

## Recommended Next Development Phases

1. Add dependency detection for endpoints.
2. Build a dependency graph for each uploaded specification.
3. Add `ExecutionPlan` and `PlanStep` models.
4. Add `ExecutionContext` for runtime variable storage.
5. Add response capture and request injection rules.
6. Update test generation to produce placeholders for dependent values.
7. Build stateful workflow execution.
8. Add topological/level-based execution with safe parallelism.
9. Add test data cleanup and teardown steps.
10. Move long-running generation/execution to background jobs.
11. Add end-to-end workflow tests and regression baselines.

## OpenAI API Key Requirement

LLM-based test generation requires an OpenAI API key through the `OPENAI_API_KEY` environment variable.

During development, a developer's personal OpenAI API key may be used temporarily. For long-term development, QA, staging, or production usage, this project should use a dedicated project-level or organization-managed OpenAI API key.

Dedicated credentials make it easier to manage:

- cost tracking
- access management
- key rotation
- security
- team-level usage
- development and production separation

## Security Notes

- The execution engine sends outbound HTTP requests to a user-provided `target_base_url`; restrict this to trusted environments.
- Uploaded specification files are stored locally under `uploads/specs`.
- API keys and tokens should be provided through environment variables or secure request-time configuration, not committed to source control.
- Personal OpenAI API keys should not be used as the long-term project credential.

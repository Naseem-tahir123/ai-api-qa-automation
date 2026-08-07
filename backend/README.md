# AI API QA Automation Platform

A FastAPI backend that turns an OpenAPI specification into executable API test cases. It stores API projects and specifications, extracts endpoints and their parameters/security requirements, uses OpenAI to generate QA coverage, executes the tests against a target API, and preserves execution history and QA reports.

## Features

- Create and manage API QA projects.
- Upload OpenAPI specifications in JSON, YAML, or YML format.
- Resolve local OpenAPI `$ref` references before storing endpoint metadata.
- Parse `GET`, `POST`, `PUT`, `DELETE`, and `PATCH` operations, including request/response schemas, path/query parameters, and security requirements.
- Generate comprehensive AI test cases for an endpoint or every endpoint in a specification.
- Generate payloads plus path and query parameter values for each test case.
- Execute one endpoint's tests or all generated tests in a specification.
- Inject Bearer-token or API-key credentials when the parsed endpoint indicates those security requirements.
- Store response data, status code, errors, timing, and pass/fail results.
- Produce specification-level QA metrics, endpoint summaries, and actionable failure details.
- Manage database changes with Alembic migrations.

## Architecture

```text
Project
  -> API Specification
      -> Endpoint (schemas, parameters, security)
          -> Test Case (payload, path params, query params)
              -> Test Result
```

```text
OpenAPI file upload
  -> parser resolves references and extracts endpoints
  -> OpenAI generates QA test cases
  -> HTTPX executes requests against the target API
  -> PostgreSQL stores results
  -> reports endpoint returns QA metrics and failure details
```

## Technology

- Python 3.11+
- FastAPI and Uvicorn
- SQLAlchemy async and asyncpg
- PostgreSQL and Alembic
- LangChain OpenAI (`gpt-4o-mini`)
- HTTPX
- PyYAML and jsonref

## Prerequisites

- Python 3.11 or later
- PostgreSQL database
- An OpenAI API key for AI-generated tests
- [uv](https://docs.astral.sh/uv/) (recommended), or another Python package manager

## Setup

1. Move into the backend directory.

   ```powershell
   cd backend
   ```

2. Create a `.env` file in this directory.

   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/api_qa_automation
   OPENAI_API_KEY=your_openai_api_key
   ```

3. Install dependencies and apply every migration, including the migrations that add endpoint security/parameters and test-case path/query parameters.

   ```powershell
   uv sync
   uv run alembic upgrade head
   ```

4. Start the API server.

   ```powershell
   uv run python main.py
   ```

The service starts at `http://localhost:8000`. Interactive Swagger documentation is available at `http://localhost:8000/docs`.

## API workflow

### 1. Check service health

```http
GET /health
```

### 2. Create a project

```http
POST /api/v1/projects/
Content-Type: application/json

{
  "name": "HR Connect API",
  "description": "QA automation for the HR backend"
}
```

### 3. Upload and parse an OpenAPI specification

Upload a `.json`, `.yaml`, or `.yml` file for an existing project.

```powershell
curl.exe -X POST "http://localhost:8000/api/v1/projects/1/specifications?version=v1" `
  -F "file=@./openapi.json"
```

Then parse the uploaded specification:

```http
POST /api/v1/specifications/{spec_id}/parse
```

Parsing replaces any endpoints previously stored for that specification. Each parsed endpoint includes its request body schema, response schema, operation parameters, and effective OpenAPI security requirement.

### 4. Generate test cases

Generate tests for one endpoint:

```http
POST /api/v1/test-cases/generate/{endpoint_id}
```

Or generate tests for every endpoint in a specification:

```http
POST /api/v1/test-cases/generate-all/{spec_id}
```

The AI is asked to create relevant happy-path, negative, boundary, validation, parameter, authentication, security, error-handling, and edge-case coverage. A test case contains its category, description, body payload, path parameters, query parameters, and expected status. Bulk generation replaces existing test cases for each endpoint before generating new ones and continues if a particular endpoint fails.

### 5. Execute tests

Provide the target API base URL in a JSON body. Credentials are optional; include the appropriate value when the specification declares Bearer or API-key security.

```http
POST /api/v1/execution/run/{endpoint_id}
Content-Type: application/json

{
  "target_base_url": "https://api.example.com",
  "auth_config": {
    "token": "your-bearer-token",
    "api_key": "your-api-key"
  }
}
```

To execute all generated tests for a specification, send the same body to:

```http
POST /api/v1/execution/run-all/{spec_id}
```

For each test, the executor substitutes saved path parameters, appends saved query parameters, sends the JSON payload where present, and compares the actual HTTP status with `expected_status`. Results include the status, response body (or a truncated raw response), elapsed time, error message, and pass/fail state.

### 6. View the QA report

```http
GET /api/v1/reports/specifications/{spec_id}
```

The report returns endpoint coverage, test totals, pass rate, total execution time, category breakdown, per-endpoint summaries, and actionable details for failed tests. It uses the latest saved result for each test case.

## API reference

| Method | Route | Description |
|---|---|---|
| `GET` | `/health` | Returns backend health status. |
| `POST` | `/api/v1/projects/` | Creates a project. |
| `GET` | `/api/v1/projects/` | Lists projects. |
| `GET` | `/api/v1/projects/{project_id}` | Retrieves a project. |
| `POST` | `/api/v1/projects/{project_id}/specifications` | Uploads an OpenAPI specification. |
| `POST` | `/api/v1/specifications/{spec_id}/parse` | Parses and saves endpoints, parameters, and security requirements. |
| `POST` | `/api/v1/test-cases/generate/{endpoint_id}` | Generates tests for one endpoint. |
| `POST` | `/api/v1/test-cases/generate-all/{spec_id}` | Regenerates tests for every endpoint in a specification. |
| `POST` | `/api/v1/execution/run/{endpoint_id}` | Runs saved tests for one endpoint. |
| `POST` | `/api/v1/execution/run-all/{spec_id}` | Runs saved tests across a specification. |
| `GET` | `/api/v1/reports/specifications/{spec_id}` | Returns the specification QA report. |

## Project structure

```text
backend/
|-- app/
|   |-- api/routes/       # FastAPI route handlers
|   |-- core/             # Environment-based configuration
|   |-- db/               # Async SQLAlchemy engine and sessions
|   |-- models/           # Database models
|   |-- schemas/          # Pydantic request and response models
|   `-- services/         # Parsing, AI generation, execution, and workflow logic
|-- alembic/              # Migration environment and revisions
|-- uploads/specs/        # Uploaded OpenAPI files (runtime data)
|-- main.py               # FastAPI application entry point
`-- pyproject.toml        # Project dependencies
```

## Database migrations

Create a migration after changing SQLAlchemy models:

```powershell
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

## Important security notes

This is a development-stage backend. Before deploying it, add authentication and authorization, enforce file-size limits, and restrict `target_base_url` to trusted hosts. The execution endpoints make outbound HTTP requests, so arbitrary target URLs can introduce server-side request forgery (SSRF) risk.

Keep `.env`, database credentials, API tokens, and `OPENAI_API_KEY` out of source control. Do not run generated tests against production systems without explicit authorization.

## Current limitations

- A test passes only when the actual and expected HTTP status codes are equal; response schemas, headers, and semantic assertions are not validated.
- The executor currently recognizes Bearer-token and `x-api-key` authentication from the stored security requirement; other OpenAPI security schemes are not interpreted.
- Endpoint parameters are read from individual operations. Path-level shared parameters are not merged automatically.
- Generating tests for one endpoint appends new records. Use bulk generation to replace test cases across a specification.
- Parsing a specification again replaces its stored endpoints and their dependent test data.
- The included LangGraph/Faker workflow is a prototype service and is not exposed through the API.

## License

No license has been specified for this project.

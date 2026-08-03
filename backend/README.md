# AI API QA Automation Platform

A FastAPI backend that turns an OpenAPI specification into executable API test cases. It stores API projects and specifications, extracts endpoints, uses OpenAI to generate positive and negative tests, executes them against a target API, and preserves the results.

## Features

- Create and manage API QA projects
- Upload OpenAPI specifications in JSON, YAML, or YML format
- Parse OpenAPI paths and persist supported endpoints
- Resolve local OpenAPI `$ref` references before storage
- Generate structured AI test cases with OpenAI
- Execute generated test cases against a configurable target base URL
- Persist HTTP status, response data, errors, timing, and pass/fail results
- Manage schema changes with Alembic migrations

## Architecture

```text
Project
  -> API Specification
      -> Endpoint
          -> Test Case
              -> Test Result
```

```text
OpenAPI file upload
  -> parser extracts endpoints
  -> OpenAI generates test cases
  -> HTTPX executes requests against target API
  -> PostgreSQL stores test history and results
```

## Technology

- Python 3.11+
- FastAPI and Uvicorn
- SQLAlchemy async and asyncpg
- PostgreSQL
- Alembic
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

3. Install dependencies.

   ```powershell
   uv sync
   ```

4. Add JWT settings to the `.env` file.

   ```env
   SECRET_KEY=your_secret_key_here
   ALGORITHM=HS256
   ```

5. Apply database migrations.

   ```powershell
   uv run alembic upgrade head
   ```

6. Start the API server.

   ```powershell
   uv run python main.py
   ```

The service starts at `http://localhost:8000`. Interactive Swagger documentation is available at `http://localhost:8000/docs`.

### Authentication endpoints

#### Signup

```http
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "demo_user",
  "password": "strong_password"
}
```

#### Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "strong_password"
}
```

The login response returns a JWT access token that can be used in the `Authorization: Bearer ...` header for protected routes later.

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

### 3. Upload an OpenAPI specification

Upload a `.json`, `.yaml`, or `.yml` file for an existing project.

```powershell
curl.exe -X POST "http://localhost:8000/api/v1/projects/1/specifications?version=v1" `
  -F "file=@./openapi.json"
```

Uploaded specifications are written to `uploads/specs/` and their metadata is stored in the database.

### 4. Parse the specification

```http
POST /api/v1/specifications/{spec_id}/parse
```

The parser supports `GET`, `POST`, `PUT`, `DELETE`, and `PATCH` operations. It stores the endpoint path, method, summary, request-body schema, and response schema.

### 5. Generate tests for an endpoint

```http
POST /api/v1/test-cases/generate/{endpoint_id}
```

The service sends the endpoint method, path, request schema, and response schema to OpenAI. It requests three structured test cases: one positive and two negative. Each generated case includes a category, description, JSON payload, and expected status code.

### 6. Run the generated tests

```http
POST /api/v1/execution/run/{endpoint_id}?target_base_url=https://api.example.com
```

For every saved test case, the execution engine sends a request to:

```text
{target_base_url}{endpoint_path}
```

A test passes when the actual HTTP status matches `expected_status`. The API saves the response body where possible, execution time, errors, status code, and pass/fail state.

## API reference

| Method | Route | Description |
|---|---|---|
| `GET` | `/health` | Returns backend health status. |
| `POST` | `/api/v1/projects/` | Creates a project. |
| `GET` | `/api/v1/projects/` | Lists projects. |
| `GET` | `/api/v1/projects/{project_id}` | Retrieves a project. |
| `POST` | `/api/v1/projects/{project_id}/specifications` | Uploads an OpenAPI specification. |
| `POST` | `/api/v1/specifications/{spec_id}/parse` | Parses and saves endpoints from a specification. |
| `POST` | `/api/v1/test-cases/generate/{endpoint_id}` | Generates AI test cases for an endpoint. |
| `POST` | `/api/v1/execution/run/{endpoint_id}` | Runs saved tests for an endpoint. |

## Project structure

```text
backend/
├── app/
│   ├── api/routes/       # FastAPI route handlers
│   ├── core/             # Environment-based configuration
│   ├── db/               # Async SQLAlchemy engine and sessions
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic request and response models
│   └── services/         # Parsing, AI generation, and execution logic
├── alembic/              # Migration environment and revisions
├── uploads/specs/        # Uploaded OpenAPI files (runtime data)
├── main.py               # FastAPI application entry point
└── pyproject.toml        # Project dependencies
```

## Database migrations

Create a migration after changing SQLAlchemy models:

```powershell
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

## Important security notes

This project is currently a development-stage backend. Before deploying it, add authentication and authorization, sanitize uploaded filenames, enforce file size limits, and restrict `target_base_url` to trusted hosts. The execution endpoint can make outbound HTTP requests, so allowing arbitrary target URLs can introduce server-side request forgery (SSRF) risk.

Keep `.env`, database credentials, and `OPENAI_API_KEY` out of source control. Do not run generated tests against production systems without explicit authorization.

## Current limitations

- Test pass/fail is based on HTTP status-code equality only.
- Response schemas, headers, query parameters, authentication, and semantic assertions are not validated automatically.
- Generating tests multiple times for the same endpoint adds more records; it does not replace existing cases.
- Parsing a specification again recreates its stored endpoints and removes their dependent test data.
- The included LangGraph/Faker workflow is a prototype service and is not exposed through the API.

## License

No license has been specified for this project.

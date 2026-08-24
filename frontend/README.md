# QA Pilot frontend

React + Vite + Tailwind frontend for the AI API QA Automation backend.

## Run locally

Start the FastAPI backend on port `8000`, then:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Vite opens the UI at `http://localhost:5173` and proxies `/api` and `/health` to the backend. For a separately hosted backend, copy `.env.example` to `.env.local` and set `VITE_API_URL`.

## Product flow

1. Sign up or log in.
2. Create a project.
3. Upload an OpenAPI JSON/YAML file.
4. Parse endpoints.
5. Generate tests with the configured AI backend.
6. Execute tests against a target API and inspect the QA report.

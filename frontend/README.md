# QA Pilot frontend

React + Vite + Tailwind frontend for the AI API QA Automation product. Authentication is integrated with FastAPI; project and QA workflows currently remain browser-local demos.

## Run locally

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Start FastAPI on `http://127.0.0.1:8000`, then open `http://127.0.0.1:5173`. Signup, login, refresh tokens, and logout use the backend authentication endpoints. Projects and QA simulations remain in browser `localStorage` until their integration phase.

## Product flow

1. Sign up or log in.
2. Create a project.
3. Upload an OpenAPI JSON/YAML file.
4. Parse endpoints.
5. Generate tests with the configured AI backend.
6. Execute tests against a target API and inspect the QA report.

## Routes

- `/login` — local/demo authentication
- `/dashboard` — workspace progress overview
- `/projects` — project directory and creation
- `/projects/:projectId` — project QA workflow
- `/projects/:projectId/report` — project-specific report
- `/reports` — quality reports overview

Protected routes redirect unauthenticated visitors to `/login`. Browser back/forward navigation and direct project URLs are supported.

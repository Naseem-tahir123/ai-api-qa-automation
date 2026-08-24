# QA Pilot frontend

React + Vite + Tailwind frontend preview for the AI API QA Automation product. It currently runs independently with browser-local demo data and makes no backend requests.

## Run locally

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open `http://127.0.0.1:5173`. No backend process is required.

Demo login:

- Email: `demo@qapilot.dev`
- Password: `demo1234`

You can also create a local account from the signup screen. Accounts, projects, and sessions are stored only in browser `localStorage`.

## Product flow

1. Sign up or log in.
2. Create a project.
3. Upload an OpenAPI JSON/YAML file.
4. Parse endpoints.
5. Generate tests with the configured AI backend.
6. Execute tests against a target API and inspect the QA report.

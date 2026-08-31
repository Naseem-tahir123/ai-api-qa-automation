from fastapi import FastAPI
from app.api.routes import auth, projects, specifications, test_cases, test_execution, reports, scenarios
from app.core.exceptions import register_exception_handlers


app = FastAPI(title="AI API QA Automation Platform", version="1.0")
register_exception_handlers(app)

# Basic health check.
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "message": "Backend and Database are connected!"}

 
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(specifications.router)
app.include_router(test_cases.router)
app.include_router(test_execution.router)
app.include_router(reports.router)
app.include_router(scenarios.router)

if __name__ == "__main__":
    import uvicorn
    # Supports starting the application with `uv run python main.py`.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

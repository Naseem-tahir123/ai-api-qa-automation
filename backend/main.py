from fastapi import FastAPI
from app.api.routes import projects, specifications, test_cases, test_execution, reports
from app.core.exceptions import register_exception_handlers

app = FastAPI(title="AI API QA Automation Platform", version="1.0")
register_exception_handlers(app)

# Basic Health Check
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "message": "Backend and Database are connected!"}

# Apne API routers ko app mein jor dein (Include karein)
app.include_router(projects.router)
app.include_router(specifications.router)
app.include_router(test_cases.router)
app.include_router(test_execution.router)
app.include_router(reports.router)

if __name__ == "__main__":
    import uvicorn
    # uv run python main.py se run karne ke liye
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

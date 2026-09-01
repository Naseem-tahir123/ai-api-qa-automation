from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.api.routes import auth, projects, specifications, test_cases, test_execution, reports
from app.core.exceptions import register_exception_handlers


app = FastAPI(title="AI API QA Automation Platform", version="1.0")
register_exception_handlers(app)

frontend_origins = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in frontend_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

if __name__ == "__main__":
    import uvicorn
    # Supports starting the application with `uv run python main.py`.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

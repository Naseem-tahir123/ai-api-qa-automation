from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, auth_profiles, pipelines, projects, specifications, qa_planning, qa_reports
from app.core.config import settings
from app.core.exceptions import register_exception_handlers


app = FastAPI(title="AI API QA Automation Platform", version="1.0")
register_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Basic health check.
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "message": "Backend and Database are connected!"}

 
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(specifications.router)
app.include_router(auth_profiles.router)
app.include_router(pipelines.router)
app.include_router(qa_planning.router)
app.include_router(qa_reports.router)

if __name__ == "__main__":
    import uvicorn
    # Supports starting the application with `uv run python main.py`.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

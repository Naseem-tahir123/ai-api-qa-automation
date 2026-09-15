import os
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Literal
from pydantic import BaseModel, HttpUrl
from werkzeug.utils import secure_filename

from app.db.database import get_db
from app.models.project import Project
from app.models.specification import APISpecification
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.specification import APISpecificationResponse
from app.schemas.environment import ProjectEnvironmentCreate, ProjectEnvironmentResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.models.environment import ProjectEnvironment
from app.services.spec_importer import RemoteSpecificationImporter, SpecificationImportError

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"], dependencies=[Depends(get_current_user)])

# Directory where uploaded API specification files will be stored.
# Create the directory automatically if it does not already exist.
UPLOAD_DIR = "uploads/specs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class SpecificationURLImportRequest(BaseModel):
    url: HttpUrl
    version: str = "v1"
    source_kind: Literal["auto", "openapi", "swagger_ui"] = "auto"


# --- 1. CREATE A NEW PROJECT ---
@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(project_in: ProjectCreate, db: AsyncSession = Depends(get_db)):
    new_project = Project(name=project_in.name, description=project_in.description)
    db.add(new_project)

    try:
        await db.commit()
        await db.refresh(new_project)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return new_project


# --- 2. RETRIEVE ALL PROJECTS ---
@router.get("/", response_model=List[ProjectResponse])
async def get_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project))
    projects = result.scalars().all()
    return projects


# --- 3. RETRIEVE A PROJECT BY ID ---
@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).filter(Project.id == project_id))
    project = result.scalar_one_or_none()

    # Return 404 if the requested project does not exist.
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


# --- 4. UPLOAD AN API SPECIFICATION FILE ---
@router.post("/{project_id}/specifications", response_model=APISpecificationResponse, status_code=201)
async def upload_specification(
    project_id: int,
    version: str = "v1",
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # Verify that the project exists before uploading the specification.
    result = await db.execute(select(Project).filter(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Accept only JSON and YAML specification files.
    if not file.filename.endswith((".json", ".yaml", ".yml")):
        raise HTTPException(
            status_code=400,
            detail="Only JSON and YAML files are allowed."
        )

    # Sanitize the filename to prevent security issues.
    safe_filename = secure_filename(file.filename)

    # Generate a unique file path for storage.
    file_path = f"{UPLOAD_DIR}/project_{project_id}_{version}_{safe_filename}"

    # Save the uploaded file asynchronously to avoid blocking the server.
    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    # Create a database record for the uploaded specification.
    new_spec = APISpecification(
        project_id=project_id,
        version=version,
        filename=file.filename,
        file_path=file_path,
        source_type="file",
    )

    db.add(new_spec)

    try:
        await db.commit()
        await db.refresh(new_spec)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database Error: {str(e)}"
        )

    return new_spec


@router.get("/{project_id}/specifications", response_model=List[APISpecificationResponse])
async def list_specifications(project_id: int, db: AsyncSession = Depends(get_db)):
    if not await db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    result = await db.execute(
        select(APISpecification)
        .where(APISpecification.project_id == project_id)
        .order_by(APISpecification.uploaded_at.desc())
    )
    return result.scalars().all()


@router.post("/{project_id}/specifications/import-url", response_model=APISpecificationResponse, status_code=201)
async def import_specification_from_url(
    project_id: int,
    request: SpecificationURLImportRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).filter(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        content, filename, resolved_url = await RemoteSpecificationImporter.fetch(
            str(request.url), request.source_kind
        )
    except SpecificationImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Security blocked this URL: {exc}") from exc

    safe_filename = secure_filename(filename)
    file_path = f"{UPLOAD_DIR}/project_{project_id}_{request.version}_{safe_filename}"
    async with aiofiles.open(file_path, "wb") as out_file:
        await out_file.write(content)

    new_spec = APISpecification(
        project_id=project_id,
        version=request.version,
        filename=filename,
        file_path=file_path,
        source_type="swagger_ui" if request.source_kind == "swagger_ui" else "openapi_url",
        source_url=resolved_url,
    )
    db.add(new_spec)
    try:
        await db.commit()
        await db.refresh(new_spec)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {exc}") from exc
    return new_spec


@router.post("/{project_id}/environments", response_model=ProjectEnvironmentResponse, status_code=201)
async def create_environment(
    project_id: int,
    environment_in: ProjectEnvironmentCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).filter(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    environment = ProjectEnvironment(project_id=project_id, **environment_in.model_dump())
    db.add(environment)
    try:
        await db.commit()
        await db.refresh(environment)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {exc}") from exc
    return environment


@router.get("/{project_id}/environments", response_model=List[ProjectEnvironmentResponse])
async def list_environments(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).filter(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(ProjectEnvironment)
        .filter(ProjectEnvironment.project_id == project_id)
        .order_by(ProjectEnvironment.created_at.desc())
    )
    return result.scalars().all()

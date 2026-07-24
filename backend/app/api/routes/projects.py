import os
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.database import get_db
from app.models.project import Project
from app.models.specification import APISpecification
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.specification import APISpecificationResponse

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])

# Uploads save karne ka folder (Agar nahi hai to automatically ban jayega)
UPLOAD_DIR = "uploads/specs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# --- 1. CREATE PROJECT (Aapka purana code) ---
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


# --- 2. GET ALL PROJECTS ---
@router.get("/", response_model=List[ProjectResponse])
async def get_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project))
    projects = result.scalars().all()
    return projects


# --- 3. GET SINGLE PROJECT BY ID ---
@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).filter(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# --- 4. UPLOAD API SPECIFICATION ---
@router.post("/{project_id}/specifications", response_model=APISpecificationResponse, status_code=201)
async def upload_specification(
    project_id: int, 
    version: str = "v1", 
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    # Check karein ke project exist karta hai ya nahi
    result = await db.execute(select(Project).filter(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Sirf JSON ya YAML allow karein
    if not file.filename.endswith((".json", ".yaml", ".yml")):
        raise HTTPException(status_code=400, detail="Only JSON and YAML files are allowed.")

    # File ko local storage mein save karein
    file_path = f"{UPLOAD_DIR}/project_{project_id}_{version}_{file.filename}"
    
    # Asynchronous file writing (taake server block na ho)
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    # Database mein entry save karein
    new_spec = APISpecification(
        project_id=project_id,
        version=version,
        filename=file.filename,
        file_path=file_path
    )
    
    db.add(new_spec)
    try:
        await db.commit()
        await db.refresh(new_spec)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

    return new_spec
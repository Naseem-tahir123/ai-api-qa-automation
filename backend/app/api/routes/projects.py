from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse

# Router setup (URLs ko group karne ke liye)
router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])

@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(project_in: ProjectCreate, db: AsyncSession = Depends(get_db)):
    # 1. User ke data se SQLAlchemy model ka instance banayein
    new_project = Project(
        name=project_in.name,
        description=project_in.description
    )
    
    # 2. Database session mein add karein
    db.add(new_project)
    
    try:
        # 3. Database mein permanently save (commit) karein
        await db.commit()
        # 4. Refresh karein taake DB se auto-generated ID aur created_at wapis mil jaye
        await db.refresh(new_project)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")
        
    return new_project

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Database se project ko ID ke basis pe fetch karein
    result = await db.get(Project, project_id)
    
    # 2. Agar project nahi mila to 404 error raise karein
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return result
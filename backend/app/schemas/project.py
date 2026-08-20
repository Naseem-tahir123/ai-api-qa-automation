from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

# Project creation request schema.
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

# Project response schema.
class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime

    # Enable serialization from SQLAlchemy model instances.
    model_config = ConfigDict(from_attributes=True)

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

# 1. API Request (Input) ke liye schema
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

# 2. API Response (Output) ke liye schema
class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime

    # Pydantic v2 syntax: SQLAlchemy Object ko JSON me convert karne ke liye
    model_config = ConfigDict(from_attributes=True)
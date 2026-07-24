from pydantic import BaseModel, ConfigDict
from datetime import datetime

# Jab file DB mein save ho jaye toh user ko yeh info wapis milegi
class APISpecificationResponse(BaseModel):
    id: int
    project_id: int
    version: str
    filename: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
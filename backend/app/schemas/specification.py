from pydantic import BaseModel, ConfigDict
from datetime import datetime

# Response returned after an API specification is stored.
class APISpecificationResponse(BaseModel):
    id: int
    project_id: int
    version: str
    filename: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EndpointResponse(BaseModel):
    id: int
    path: str
    method: str
    summary: str | None

    model_config = ConfigDict(from_attributes=True)

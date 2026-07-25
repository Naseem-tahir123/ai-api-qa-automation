from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class Endpoint(Base):
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)
    specification_id = Column(Integer, ForeignKey("api_specifications.id", ondelete="CASCADE"), nullable=False)
    
    path = Column(String, nullable=False)        # e.g., /api/v1/users
    method = Column(String, nullable=False)      # e.g., POST, GET
    summary = Column(String, nullable=True)      # Description
    
    # JSON columns taake API ka structure (rules) save ho sake
    request_schema = Column(JSON, nullable=True)
    response_schema = Column(JSON, nullable=True)

    # Relationship setup
    specification = relationship("APISpecification", back_populates="endpoints")
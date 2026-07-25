from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

class APISpecification(Base):
    __tablename__ = "api_specifications"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    version = Column(String, nullable=False, default="v1")
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False) # File jahan local disk par save hogi
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship setup (Ek spec kis project se belong karti hai)
    project = relationship("Project", back_populates="specifications")
    endpoints = relationship("Endpoint", back_populates="specification", cascade="all, delete-orphan")
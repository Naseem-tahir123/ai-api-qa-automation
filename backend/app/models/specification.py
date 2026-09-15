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
    file_path = Column(String, nullable=False)  # Local path of the uploaded file.
    source_type = Column(String, nullable=False, default="file", server_default="file")
    source_url = Column(String, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Each API specification belongs to one project.
    project = relationship("Project", back_populates="specifications")
    endpoints = relationship("Endpoint", back_populates="specification", cascade="all, delete-orphan")
    qa_ir_snapshot = relationship("QAIRSnapshot", back_populates="specification", cascade="all, delete-orphan", uselist=False)
    coverage_plans = relationship("CoveragePlan", back_populates="specification", cascade="all, delete-orphan")

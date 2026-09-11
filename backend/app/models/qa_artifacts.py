"""Persisted planning artefacts; JSON keeps the QA model extensible per OpenAPI version."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class QAIRSnapshot(Base):
    __tablename__ = "qa_ir_snapshots"

    id = Column(Integer, primary_key=True)
    specification_id = Column(Integer, ForeignKey("api_specifications.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    fingerprint = Column(String(64), nullable=False, index=True)
    schema_version = Column(String(32), nullable=False, default="qa-ir/v1")
    document = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    specification = relationship("APISpecification", back_populates="qa_ir_snapshot")


class CoveragePlan(Base):
    __tablename__ = "coverage_plans"

    id = Column(Integer, primary_key=True)
    specification_id = Column(Integer, ForeignKey("api_specifications.id", ondelete="CASCADE"), nullable=False, index=True)
    fingerprint = Column(String(64), nullable=False, index=True)
    policy_version = Column(String(32), nullable=False, default="coverage/v1")
    plan = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    specification = relationship("APISpecification", back_populates="coverage_plans")

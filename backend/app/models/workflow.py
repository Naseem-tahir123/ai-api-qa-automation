from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class WorkflowPlan(Base):
    __tablename__ = "workflow_plans"

    id = Column(Integer, primary_key=True, index=True)
    specification_id = Column(Integer, ForeignKey("api_specifications.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft")
    graph = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    steps = relationship("WorkflowStep", back_populates="plan", cascade="all, delete-orphan", order_by="WorkflowStep.position")
    runs = relationship("WorkflowRun", back_populates="plan", cascade="all, delete-orphan")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("workflow_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    depends_on = Column(JSON, nullable=False, default=list)
    capture_rules = Column(JSON, nullable=False, default=list)
    injection_rules = Column(JSON, nullable=False, default=list)
    is_cleanup = Column(Boolean, nullable=False, default=False)

    plan = relationship("WorkflowPlan", back_populates="steps")
    endpoint = relationship("Endpoint")


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("workflow_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, default="running")
    runtime_context = Column(JSON, nullable=False, default=dict)
    step_results = Column(JSON, nullable=False, default=list)
    summary = Column(JSON, nullable=False, default=dict)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    plan = relationship("WorkflowPlan", back_populates="runs")

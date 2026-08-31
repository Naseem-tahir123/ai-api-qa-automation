from sqlalchemy import Column, Integer, String, JSON, Boolean, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)
    scenario_step_id = Column(Integer, ForeignKey("scenario_steps.id", ondelete="CASCADE"), nullable=False)
    
    actual_status = Column(Integer, nullable=True)  # HTTP status returned by the target API.
    is_passed = Column(Boolean, nullable=False, default=False)  # Whether the test passed.
    response_body = Column(JSON, nullable=True)  # Response body returned by the target API.
    execution_time_ms = Column(Float, nullable=True)  # Request duration in milliseconds.
    error_message = Column(String, nullable=True)  # Connection or execution failure details.
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

    step = relationship("ScenarioStep", back_populates="results")

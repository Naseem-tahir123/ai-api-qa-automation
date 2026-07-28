from sqlalchemy import Column, Integer, String, JSON, Boolean, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    
    actual_status = Column(Integer, nullable=True)          # e.g., Target API ne kya status wapis diya
    is_passed = Column(Boolean, nullable=False, default=False) # True (Pass) ya False (Fail)
    response_body = Column(JSON, nullable=True)             # Target API ka response body
    execution_time_ms = Column(Float, nullable=True)        # Request hone mein kitne ms lage
    error_message = Column(String, nullable=True)           # Agar server down tha ya connection fail hua
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

    test_case = relationship("TestCase", back_populates="results")
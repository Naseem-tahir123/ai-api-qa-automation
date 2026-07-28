from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base

class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_id = Column(Integer, ForeignKey("endpoints.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, nullable=False) # e.g., "Positive", "Negaative", "Boundary"
    description = Column(String, nullable=False) # Detail of test case
    payload = Column(JSON, nullable=True) # Request Body (Faker/AI generated data)
    expected_status = Column(Integer, nullable=False)  # e.g., 200, 201, 400

    endpoint = relationship("Endpoint", back_populates="test_cases")
    results = relationship("TestResult", back_populates="test_case", cascade="all, delete-orphan")


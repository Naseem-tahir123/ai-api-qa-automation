from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base


class Endpoint(Base):
    __tablename__ = "endpoints"

    id = Column(Integer, primary_key=True, index=True)

    specification_id = Column(
        Integer,
        ForeignKey("api_specifications.id", ondelete="CASCADE"),
        nullable=False
    )

    path = Column(String, nullable=False)        # API endpoint path, e.g., /api/v1/users
    method = Column(String, nullable=False)      # HTTP method, e.g., POST, GET
    summary = Column(String, nullable=True)      # Short description of the endpoint

    # JSON columns to store API request and response structures.
    request_schema = Column(JSON, nullable=True)
    response_schema = Column(JSON, nullable=True)
    parameters = Column(JSON, nullable=True)
    security = Column(JSON, nullable=True)

    # Define relationships with related database models.
    specification = relationship("APISpecification", back_populates="endpoints")
    test_cases = relationship(
        "TestCase",
        back_populates="endpoint",
        cascade="all, delete-orphan"
    )
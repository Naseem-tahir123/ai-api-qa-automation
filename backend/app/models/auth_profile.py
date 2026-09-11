from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class AuthProfile(Base):
    """Reusable, non-secret authentication configuration for an environment."""

    __tablename__ = "auth_profiles"

    id = Column(Integer, primary_key=True, index=True)
    environment_id = Column(Integer, ForeignKey("project_environments.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    auth_type = Column(String, nullable=False)  # login, bearer, api_key, basic
    injection_rules = Column(JSON, nullable=False, default=dict)
    login_config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    environment = relationship("ProjectEnvironment", back_populates="auth_profiles")
    identities = relationship("TestIdentity", back_populates="auth_profile", cascade="all, delete-orphan")


class TestIdentity(Base):
    """A named QA role with an encrypted credential bundle."""

    __tablename__ = "test_identities"

    id = Column(Integer, primary_key=True, index=True)
    auth_profile_id = Column(Integer, ForeignKey("auth_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=True)
    encrypted_secret = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    auth_profile = relationship("AuthProfile", back_populates="identities")

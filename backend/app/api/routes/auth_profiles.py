from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.auth_profile import AuthProfile, TestIdentity
from app.models.environment import ProjectEnvironment
from app.schemas.auth_profile import (
    AuthProfileCreate,
    AuthProfileResponse,
    TestIdentityCreate,
    TestIdentityResponse,
)
from app.services.secrets import SecretConfigurationError, SecretProtector


router = APIRouter(
    prefix="/api/v1/auth-profiles",
    tags=["Target API Authentication"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=AuthProfileResponse, status_code=201)
async def create_auth_profile(profile_in: AuthProfileCreate, db: AsyncSession = Depends(get_db)):
    environment = await db.get(ProjectEnvironment, profile_in.environment_id)
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")

    profile = AuthProfile(**profile_in.model_dump())
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/environment/{environment_id}", response_model=List[AuthProfileResponse])
async def list_auth_profiles(environment_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuthProfile).filter(AuthProfile.environment_id == environment_id).order_by(AuthProfile.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{profile_id}/identities", response_model=TestIdentityResponse, status_code=201)
async def create_test_identity(
    profile_id: int,
    identity_in: TestIdentityCreate,
    db: AsyncSession = Depends(get_db),
):
    profile = await db.get(AuthProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Auth profile not found")
    try:
        encrypted_secret = SecretProtector.encrypt(identity_in.secrets)
    except SecretConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    identity = TestIdentity(
        auth_profile_id=profile.id,
        name=identity_in.name,
        role=identity_in.role,
        encrypted_secret=encrypted_secret,
    )
    db.add(identity)
    await db.commit()
    await db.refresh(identity)
    return identity


@router.get("/{profile_id}/identities", response_model=List[TestIdentityResponse])
async def list_test_identities(profile_id: int, db: AsyncSession = Depends(get_db)):
    if not await db.get(AuthProfile, profile_id):
        raise HTTPException(status_code=404, detail="Auth profile not found")
    result = await db.execute(
        select(TestIdentity).filter(TestIdentity.auth_profile_id == profile_id).order_by(TestIdentity.created_at.desc())
    )
    return result.scalars().all()

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
import jwt

from app.db.database import get_db
from app.models.user import User
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
from app.core.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Helper functions for password hashing and JWT token creation ---

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# --- Signup endpoint: create user and save into the database ---
@router.post("/signup", response_model=UserResponse, status_code=201)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_user = await db.scalar(select(User).where(User.email == user_in.email))
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_username = await db.scalar(select(User).where(User.username == user_in.username))
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")

    new_user = User(
        email=str(user_in.email),
        username=user_in.username,
        password_hash=hash_password(user_in.password),
    )
    db.add(new_user)

    try:
        await db.commit()
        await db.refresh(new_user)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    return new_user


# --- Login endpoint: verify credentials and return JWT token ---
@router.post("/login", response_model=TokenResponse)
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == str(user_in.email)))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)

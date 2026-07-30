from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

# Engine: Makes connection from Database
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Session: It is useful for insert/read data into database
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Dependency injection (To use in FastAPI)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
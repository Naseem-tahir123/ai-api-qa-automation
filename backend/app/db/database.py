from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

# Engine: Database se connection banata hai
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# Session: Database mein query (insert/read) karne ke kaam aata hai
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Dependency injection (FastAPI mein use karne ke liye)
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
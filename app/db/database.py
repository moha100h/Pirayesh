from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.db.models import Base
from app.config import config
import os

# اطمینان از وجود پوشه data
db_path = config.DATABASE_URL.replace("sqlite+aiosqlite:////", "/")
os.makedirs(os.path.dirname(db_path), exist_ok=True)

engine = create_async_engine(config.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

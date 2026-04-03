from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_async_engine("postgresql+asyncpg://postgres:123456@172.28.243.133:5432/chat_db",echo=False,future=True)
AsyncSessionLocal = async_sessionmaker(engine,expire_on_commit=False,class_=AsyncSession)
Base = declarative_base()
#异步获取数据库
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
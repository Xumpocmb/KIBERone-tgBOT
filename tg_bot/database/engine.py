import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from tg_bot.database.models import Base
from dotenv import load_dotenv

load_dotenv()

engine = create_async_engine(os.getenv('DATABASE_URL'), echo=False)
session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=True)


async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


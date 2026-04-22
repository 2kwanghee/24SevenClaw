import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    engine = create_async_engine("postgresql+asyncpg://clickeye:devpassword@localhost:5432/clickeye")
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print("Connected:", result.fetchone())

asyncio.run(test())

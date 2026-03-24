import asyncio
import structlog
from db.seed import run_seed
from db.session import engine
from sqlmodel.ext.asyncio.session import AsyncSession

async def main():
    async with AsyncSession(engine) as session:
        await run_seed(session)

if __name__ == "__main__":
    asyncio.run(main())

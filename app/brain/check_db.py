
import asyncio
from sqlalchemy import select, func
from app.core.database.base import AsyncSessionLocal
from app.features.models import Company, Job

async def check_data():
    async with AsyncSessionLocal() as db:
        company_count = await db.execute(select(func.count(Company.id)))
        job_count = await db.execute(select(func.count(Job.id)))
        
        print(f"Total Companies in DB: {company_count.scalar()}")
        print(f"Total Jobs in DB: {job_count.scalar()}")

if __name__ == "__main__":
    asyncio.run(check_data())

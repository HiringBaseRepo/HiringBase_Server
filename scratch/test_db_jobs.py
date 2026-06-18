import asyncio
from sqlalchemy import select
from app.main import app  # registers all models
from app.core.database.base import get_db
from app.features.jobs.models import Job

async def main():
    async for db in get_db():
        stmt = select(Job)
        result = await db.execute(stmt)
        jobs = result.scalars().all()
        for job in jobs:
            print(f"ID: {job.id}, Title: {job.title}")
            print(f"  Description: {job.description}")
            print(f"  Responsibilities: {job.responsibilities}")
            print(f"  Benefits: {job.benefits}")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import all models to register them
from app.features.models import *
from app.features.users.models import User
from app.features.jobs.models import Job
from app.features.applications.models import Application
from app.shared.enums.job_status import JobStatus

DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_uDYhfcpiy8w1@ep-bitter-forest-aoc1v14g-pooler.c-2.ap-southeast-1.aws.neon.tech/HireBase?ssl=require"

async def check():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check hiringbase52@gmail.com
        user_result = await session.execute(select(User).where(User.email == "hiringbase52@gmail.com"))
        user = user_result.scalar_one_or_none()
        if user:
            print(f"User: {user.email}, Company ID: {user.company_id}")
            jobs_result = await session.execute(select(Job).where(Job.company_id == user.company_id))
            jobs = jobs_result.scalars().all()
            print(f"Total jobs: {len(jobs)}")
            for j in jobs:
                apps_result = await session.execute(
                    select(Application).where(Application.job_id == j.id)
                )
                apps = apps_result.scalars().all()
                print(f"  Job ID: {j.id}, Title: {j.title}, Status: {j.status.value}, Created: {j.created_at}, Applicants: {len(apps)}")
                for app in apps:
                    print(f"    Application ID: {app.id}, Status: {app.status.value}, Applied At: {app.created_at}")
        else:
            print("User hiringbase52@gmail.com not found")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())

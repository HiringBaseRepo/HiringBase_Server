import asyncio
from sqlalchemy import select
from app.core.database.base import AsyncSessionLocal
from app.features.jobs.models import JobFormField

async def check():
    async with AsyncSessionLocal() as db:
        fields = await db.execute(select(JobFormField).where(JobFormField.job_id == 671))
        f_list = fields.scalars().all()
        print(f"FIELDS_COUNT for Job 671: {len(f_list)}")
        for f in f_list:
            print(f" - Field: key='{f.field_key}', label='{f.label}'")

if __name__ == "__main__":
    asyncio.run(check())

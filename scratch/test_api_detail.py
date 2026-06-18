import asyncio
from app.main import app  # registers all models
from app.features.applications.services.public_service import get_public_job_detail
from app.core.database.base import get_db

async def main():
    async for db in get_db():
        try:
            # Let's test for Job ID 712 (Web Service)
            res = await get_public_job_detail(db, 712)
            print("Job ID 712 Details:")
            print(f"Title: {res.title}")
            print(f"Description: {res.description}")
            print(f"Responsibilities: {res.responsibilities}")
            print(f"Benefits: {res.benefits}")
            print(f"Requirements: {res.requirements}")
            print(f"Form Fields: {res.form_fields}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

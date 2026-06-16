import asyncio
from app.features.models import *
from app.core.database.base import AsyncSessionLocal
from app.features.applications.repositories.repository import get_form_fields_by_job_id

async def main():
    # initialize DB
    async with AsyncSessionLocal() as session:
        fields = await get_form_fields_by_job_id(session, 698)
        for f in fields:
            print(f"ID: {f.id}, Key: {f.field_key}, Label: {f.label}, Type: {f.field_type}, Required: {f.is_required}")

if __name__ == "__main__":
    asyncio.run(main())

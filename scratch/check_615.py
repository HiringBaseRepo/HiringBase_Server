import asyncio
from sqlalchemy import select
from app.core.database.base import AsyncSessionLocal
from app.features.applications.models import ApplicationAnswer, ApplicationDocument

async def check():
    async with AsyncSessionLocal() as db:
        ans = await db.execute(select(ApplicationAnswer).where(ApplicationAnswer.application_id == 615))
        docs = await db.execute(select(ApplicationDocument).where(ApplicationDocument.application_id == 615))
        a_list = ans.scalars().all()
        d_list = docs.scalars().all()
        print(f"ANS_COUNT: {len(a_list)}")
        print(f"DOC_COUNT: {len(d_list)}")
        for a in a_list:
            print(f" - Answer: FieldID={a.form_field_id}, Val={a.value_text or a.value_number}")
        for d in d_list:
            print(f" - Doc: {d.file_name}")

if __name__ == "__main__":
    asyncio.run(check())

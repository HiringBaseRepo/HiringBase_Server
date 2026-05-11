import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.features.applications.models import Application, ApplicationDocument

async def check_app():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        app_id = 628
        result = await db.execute(select(Application).where(Application.id == app_id))
        app = result.scalar_one_or_none()
        
        if not app:
            print(f"Application {app_id} NOT FOUND")
            return
            
        print(f"Application {app_id} status: {app.status}")
        
        doc_result = await db.execute(select(ApplicationDocument).where(ApplicationDocument.application_id == app_id))
        docs = doc_result.scalars().all()
        print(f"Found {len(docs)} documents for application {app_id}")
        for doc in docs:
            print(f"  - Doc ID: {doc.id}, Type: {doc.document_type}, File: {doc.file_name}")

if __name__ == "__main__":
    asyncio.run(check_app())

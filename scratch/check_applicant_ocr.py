import asyncio
import os
import sys
import pkgutil
import importlib

# Add project root to sys.path
sys.path.append(os.getcwd())

# Dynamically import all models
for _, module_name, is_pkg in pkgutil.walk_packages(path=['app/features'], prefix='app.features.'):
    if 'models' in module_name:
        try:
            importlib.import_module(module_name)
        except Exception:
            pass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from app.core.config import settings
from app.features.applications.models import Application, ApplicationDocument

async def check_ocr():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        for app_id in [709, 710]:
            print(f"\n=== Application ID: {app_id} ===")
            stmt = (
                select(Application)
                .options(
                    selectinload(Application.applicant),
                    selectinload(Application.documents)
                )
                .where(Application.id == app_id)
            )
            res = await db.execute(stmt)
            app = res.scalar_one_or_none()
            if not app:
                print("Not found")
                continue
                
            print(f"Applicant Full Name: '{app.applicant.full_name if app.applicant else 'N/A'}'")
            print(f"Documents count: {len(app.documents)}")
            for doc in app.documents:
                print("-" * 40)
                print(f"Doc Type: {doc.document_type}")
                print(f"File Name: {doc.file_name}")
                print(f"File URL: {doc.file_url}")
                print(f"OCR Text (first 500 chars):\n{doc.ocr_text}")
                print("-" * 40)

if __name__ == "__main__":
    asyncio.run(check_ocr())

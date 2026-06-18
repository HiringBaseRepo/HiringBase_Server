import asyncio
import os
import sys
import json
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
from app.features.applications.models import Application, ApplicationDocument, ApplicationStatusLog
from app.features.screening.models import CandidateScore

async def find_rejections():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Get all rejected or doc_failed applications
        stmt = (
            select(Application)
            .options(
                selectinload(Application.applicant),
                selectinload(Application.job),
                selectinload(Application.documents)
            )
            .order_by(Application.id.desc())
            .limit(30)
        )
        result = await db.execute(stmt)
        applications = result.scalars().all()
        
        print(f"Checking the last {len(applications)} applications for rejections:\n")
        
        for app in applications:
            # Let's count documents
            doc_count = len(app.documents)
            
            # Fetch CandidateScore
            score_stmt = select(CandidateScore).where(CandidateScore.application_id == app.id)
            score_res = await db.execute(score_stmt)
            score = score_res.scalar_one_or_none()
            
            status_val = app.status.value if hasattr(app.status, "value") else str(app.status)
            
            if "rejected" in status_val.lower() or "failed" in status_val.lower():
                print("=" * 60)
                print(f"Application ID   : {app.id}")
                print(f"Applicant Name   : {app.applicant.full_name if app.applicant else 'N/A'}")
                print(f"Status           : {status_val}")
                print(f"Document Count   : {doc_count}")
                print("Uploaded Docs    :")
                for d in app.documents:
                    print(f"  - Type: {d.document_type}, File: {d.file_name}")
                
                if score:
                    print(f"Risk Level       : {score.risk_level}")
                    print("Red Flags        :")
                    print(json.dumps(score.red_flags, indent=2))
                else:
                    print("No CandidateScore record.")
                    
                # Fetch status logs
                log_stmt = (
                    select(ApplicationStatusLog)
                    .where(ApplicationStatusLog.application_id == app.id)
                    .order_by(ApplicationStatusLog.id.asc())
                )
                log_res = await db.execute(log_stmt)
                logs = log_res.scalars().all()
                print("Status Logs      :")
                for log in logs:
                    print(f"  - {log.from_status} -> {log.to_status} | Reason: {log.reason}")
                print("=" * 60 + "\n")

if __name__ == "__main__":
    asyncio.run(find_rejections())

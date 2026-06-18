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
from app.features.screening.services.orchestrator import process_screening
from app.features.screening.models import CandidateScore
from app.features.applications.models import Application, ApplicationStatusLog
from app.features.jobs.models import Job

async def recheck_screening():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        app_id = 710
        print(f"Re-running screening for Application ID: {app_id}...")
        
        # Load Application and Job to get company_id
        app_res = await db.execute(
            select(Application)
            .options(selectinload(Application.job))
            .where(Application.id == app_id)
        )
        app = app_res.scalar_one_or_none()
        
        if not app:
            print(f"Application {app_id} not found.")
            return
            
        company_id = app.job.company_id
        
        # Re-run screening (using force_fallback=False for real API call)
        await process_screening(
            application_id=app_id,
            company_id=company_id,
            trigger_source="retest_fix"
        )
        
        print("Screening process finished. Fetching result...")
        
        # Refresh the app object from db
        await db.refresh(app)
        print(f"New Application Status: {app.status}")
        
        score_res = await db.execute(select(CandidateScore).where(CandidateScore.application_id == app_id))
        score = score_res.scalar_one_or_none()
        
        if score:
            print(f"Final Score      : {score.final_score}")
            print(f"Risk Level       : {score.risk_level}")
            print(f"Admin Score      : {score.administrative_score}")
            print("Red Flags        :")
            print(json.dumps(score.red_flags, indent=2))
            print("Explanation      :")
            print(score.explanation)
        else:
            print("No CandidateScore record found.")
            
        # Status logs
        log_res = await db.execute(
            select(ApplicationStatusLog)
            .where(ApplicationStatusLog.application_id == app_id)
            .order_by(ApplicationStatusLog.id.desc())
            .limit(3)
        )
        logs = log_res.scalars().all()
        print("\nLatest Status Logs:")
        for log in logs:
            print(f"  - {log.from_status} -> {log.to_status} | Reason: {log.reason}")

if __name__ == "__main__":
    asyncio.run(recheck_screening())

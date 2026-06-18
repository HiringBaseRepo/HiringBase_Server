import asyncio
import os
import sys
import json
import pkgutil
import importlib

# Add project root to sys.path
sys.path.append(os.getcwd())

# Dynamically import all models under app.features to register them with Base
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

async def check_rejected_apps():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Get latest 15 applications
        stmt = (
            select(Application)
            .options(
                selectinload(Application.applicant),
                selectinload(Application.job)
            )
            .order_by(Application.id.desc())
            .limit(15)
        )
        result = await db.execute(stmt)
        applications = result.scalars().all()
        
        if not applications:
            print("No applications found in database.")
            return
            
        print(f"Found {len(applications)} recent applications:\n")
        
        for app in applications:
            print("=" * 60)
            print(f"Application ID   : {app.id}")
            print(f"Job Title (ID)   : {app.job.title if app.job else 'N/A'} ({app.job_id})")
            print(f"Applicant Name   : {app.applicant.full_name if app.applicant else 'N/A'}")
            print(f"Applicant Email  : {app.applicant.email if app.applicant else 'N/A'}")
            print(f"Status           : {app.status}")
            print(f"Created At       : {app.created_at}")
            
            # Fetch CandidateScore
            from app.features.screening.models import CandidateScore
            score_stmt = select(CandidateScore).where(CandidateScore.application_id == app.id)
            score_res = await db.execute(score_stmt)
            score = score_res.scalar_one_or_none()
            
            if score:
                print(f"Final Score      : {score.final_score}")
                print(f"Risk Level       : {score.risk_level}")
                print(f"Skill Match Score: {score.skill_match_score}")
                print(f"Experience Score : {score.experience_score}")
                print(f"Education Score  : {score.education_score}")
                print(f"Portfolio Score  : {score.portfolio_score}")
                print(f"Soft Skill Score : {score.soft_skill_score}")
                print(f"Admin Score      : {score.administrative_score}")
                print("Red Flags        :")
                print(json.dumps(score.red_flags, indent=2))
                print("Scoring Breakdown Gates:")
                if score.scoring_breakdown:
                    print(json.dumps(score.scoring_breakdown.get("gates", {}), indent=2))
                    print("Administrative Component:")
                    print(json.dumps(score.scoring_breakdown.get("components", {}).get("administrative", {}), indent=2))
                print(f"Explanation      :\n{score.explanation}")
            else:
                print("No CandidateScore record found.")
                
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
    asyncio.run(check_rejected_apps())

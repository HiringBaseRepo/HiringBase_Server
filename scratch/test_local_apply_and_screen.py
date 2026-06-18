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
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.features.applications.schemas.schema import PublicApplyCommand
from app.features.applications.services.public_service import public_apply
from app.features.screening.services.orchestrator import process_screening
from app.features.screening.models import CandidateScore
from app.features.applications.models import Application, ApplicationStatusLog
from fastapi import UploadFile
import io

async def test_apply_and_screen():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        print("1. Submitting Public Application with VALID data...")
        
        job_id = 698
        email = "john.valid.local@test.com"
        full_name = "John Test"
        phone = "081234567890"
        
        answers = {
            "education": "Bachelor's Degree in Computer Science",
            "work_experience": "I have 5 years of experience as a software engineer specializing in python, flutter, node.js, and DWH systems.",
            "skills": "Python, Flutter, Node.js, DWH, JavaScript, FastAPI",
            "experience": "5 years"
        }
        
        command = PublicApplyCommand(
            job_id=job_id,
            email=email,
            full_name=full_name,
            phone=phone,
            answers_json=json.dumps(answers)
        )
        
        # We upload only portfolio (CV) to avoid document name-matching validation
        # Create a mock file
        mock_file_content = b"%PDF-1.4 mock cv pdf content for John Test"
        upload_file = UploadFile(
            file=io.BytesIO(mock_file_content),
            filename="portfolio.pdf",
            headers={"content-type": "application/pdf"}
        )
        
        from app.shared.enums.document_type import DocumentType
        documents_data = [
            {"type": DocumentType.PORTFOLIO, "file": upload_file}
        ]
        
        # Run public_apply
        result = await public_apply(db, data=command, documents_data=documents_data)
        app_id = result.application_id
        ticket_code = result.ticket_code
        
        print(f"   -> Application created successfully! ID: {app_id}, Ticket Code: {ticket_code}")
        
        print("\n2. Triggering AI Screening Process locally...")
        # Run the screening orchestrator
        # We set trigger_source="manual"
        # The company_id for job 698 is 10 (or let's check it, we can pass None or load it)
        # Let's get the job to find company_id
        from app.features.jobs.models import Job
        job_res = await db.execute(select(Job).where(Job.id == job_id))
        job = job_res.scalar_one()
        company_id = job.company_id
        
        await process_screening(
            application_id=app_id,
            company_id=company_id,
            trigger_source="manual_test"
        )
        
        print("   -> Screening process completed!")
        
        # Refresh session and fetch candidate score
        print("\n3. Verifying Screening Result from Database:")
        
        app_res = await db.execute(select(Application).where(Application.id == app_id))
        app = app_res.scalar_one()
        print(f"   -> Final Application Status: {app.status}")
        
        score_res = await db.execute(select(CandidateScore).where(CandidateScore.application_id == app_id))
        score = score_res.scalar_one_or_none()
        
        if score:
            print(f"   -> Final Score      : {score.final_score}")
            print(f"   -> Risk Level       : {score.risk_level}")
            print(f"   -> Skill Match Score: {score.skill_match_score}")
            print(f"   -> Experience Score : {score.experience_score}")
            print(f"   -> Education Score  : {score.education_score}")
            print(f"   -> Portfolio Score  : {score.portfolio_score}")
            print(f"   -> Soft Skill Score : {score.soft_skill_score}")
            print(f"   -> Admin Score      : {score.administrative_score}")
            print("   -> Red Flags        :")
            print(json.dumps(score.red_flags, indent=2))
            print("   -> Explanation      :")
            print(score.explanation)
        else:
            print("   -> ERROR: No CandidateScore record found!")
            
        # Status logs
        log_res = await db.execute(
            select(ApplicationStatusLog)
            .where(ApplicationStatusLog.application_id == app_id)
            .order_by(ApplicationStatusLog.id.asc())
        )
        logs = log_res.scalars().all()
        print("\n4. Status Log History:")
        for log in logs:
            print(f"   - {log.from_status} -> {log.to_status} | Reason: {log.reason}")

if __name__ == "__main__":
    asyncio.run(test_apply_and_screen())

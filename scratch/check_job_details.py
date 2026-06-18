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
from app.features.jobs.models import Job, JobFormField, JobKnockoutRule, JobRequirement

async def check_job():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        job_id = 698
        job_res = await db.execute(select(Job).where(Job.id == job_id))
        job = job_res.scalar_one_or_none()
        
        if not job:
            print(f"Job {job_id} not found.")
            return
            
        print(f"Job ID: {job.id}")
        print(f"Title: {job.title}")
        print(f"Description: {job.description}")
        
        # Form fields
        ff_res = await db.execute(select(JobFormField).where(JobFormField.job_id == job_id))
        fields = ff_res.scalars().all()
        print("\nForm Fields:")
        for f in fields:
            print(f"  - Key: {f.field_key}, Type: {f.field_type}, Label: {f.label}, Required: {f.is_required}")
            
        # Knockout rules
        kr_res = await db.execute(select(JobKnockoutRule).where(JobKnockoutRule.job_id == job_id))
        rules = kr_res.scalars().all()
        print("\nKnockout Rules:")
        for r in rules:
            print(f"  - Name: {r.rule_name}, Type: {r.rule_type}, Field: {r.field_key}, Target: {r.target_value}, Op: {r.operator}, Active: {r.is_active}")
            
        # Requirements
        req_res = await db.execute(select(JobRequirement).where(JobRequirement.job_id == job_id))
        reqs = req_res.scalars().all()
        print("\nRequirements:")
        for req in reqs:
            print(f"  - Category: {req.category}, Name: {req.name}, Value: {req.value}, Required: {req.is_required}")

if __name__ == "__main__":
    asyncio.run(check_job())

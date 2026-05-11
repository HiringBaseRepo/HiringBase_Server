
import asyncio
from sqlalchemy import select
from app.core.database.session import get_db
from app.features.jobs.models import JobScoringTemplate

async def check_template():
    async for db in get_db():
        result = await db.execute(select(JobScoringTemplate).where(JobScoringTemplate.job_id == 671))
        template = result.scalar_one_or_none()
        if template:
            print(f"Skill weight: {template.skill_match_weight}")
            print(f"Exp weight: {template.experience_weight}")
            print(f"Edu weight: {template.education_weight}")
            print(f"Portfolio weight: {template.portfolio_weight}")
            print(f"Soft skill weight: {template.soft_skill_weight}")
            print(f"Admin weight: {template.administrative_weight}")
        else:
            print("No template found for job 671")
        break

if __name__ == "__main__":
    asyncio.run(check_template())

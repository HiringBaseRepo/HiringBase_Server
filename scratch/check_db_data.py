import asyncio
from sqlalchemy import select, func
from app.core.database.base import engine, AsyncSessionLocal
from app.features.models import Application, CandidateScore, Company, Job # Import from models aggregator

async def check_data():
    async with AsyncSessionLocal() as db:
        try:
            # Check Companies
            comp_stmt = select(func.count(Company.id))
            comp_count = (await db.execute(comp_stmt)).scalar()
            print(f"Total Companies: {comp_count}")

            # Check Applications
            app_stmt = select(func.count(Application.id))
            app_count = (await db.execute(app_stmt)).scalar()
            print(f"Total Applications: {app_count}")

            # Check Scores
            score_stmt = select(func.count(CandidateScore.id))
            score_count = (await db.execute(score_stmt)).scalar()
            print(f"Total Scores: {score_count}")

            # Test the specific query for screening volume
            stmt = (
                select(
                    func.to_char(Application.created_at, 'Mon DD').label('date_label'),
                    func.count(Application.id).label('count')
                )
                .group_by(func.to_char(Application.created_at, 'Mon DD'))
                .order_by(func.min(Application.created_at))
            )
            res = await db.execute(stmt)
            rows = res.all()
            print(f"Screening Volume Rows: {rows}")
        except Exception as e:
            print(f"Error during execution: {e}")

if __name__ == "__main__":
    asyncio.run(check_data())

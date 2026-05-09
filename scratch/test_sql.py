import asyncio
from sqlalchemy import select, func, text
from app.core.database.base import engine, AsyncSessionLocal
from app.features.models import Application

async def test_query():
    async with AsyncSessionLocal() as db:
        try:
            stmt = (
                select(
                    func.to_char(Application.created_at, 'Mon DD').label('date_label'),
                    func.count(Application.id).label('count'),
                    func.min(Application.created_at).label('sort_key')
                )
                .group_by(text('date_label'))
                .order_by(text('sort_key'))
            )
            res = await db.execute(stmt)
            print(f"Query Success! Rows: {res.all()}")
        except Exception as e:
            print(f"Query Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_query())

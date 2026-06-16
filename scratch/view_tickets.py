import asyncio
from sqlalchemy import select
from app.features.models import *
from app.core.database.base import AsyncSessionLocal
from app.features.tickets.models import Ticket
from app.features.applications.models import Application

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Ticket).order_by(Ticket.id.desc()).limit(10))
        tickets = result.scalars().all()
        print(f"--- LAST 10 TICKETS ---")
        for t in tickets:
            print(f"ID: {t.id}, Code: {t.code}, Status: {t.status}, ApplicationID: {t.application_id}")

        result_apps = await session.execute(select(Application).order_by(Application.id.desc()).limit(10))
        apps = result_apps.scalars().all()
        print(f"--- LAST 10 APPLICATIONS ---")
        for a in apps:
            print(f"ID: {a.id}, JobID: {a.job_id}, Status: {a.status}, Ticket: {a.ticket_code if hasattr(a, 'ticket_code') else 'N/A'}")

if __name__ == "__main__":
    asyncio.run(main())

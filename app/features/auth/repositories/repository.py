"""Auth data access helpers."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.models import Company, User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def save_user(db: AsyncSession, user: User) -> User:
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def save_company(db: AsyncSession, company: Company) -> Company:
    db.add(company)
    await db.flush()
    await db.refresh(company)
    return company

"""Auth data access helpers."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.companies.models import Company
from app.features.users.models import User, RefreshToken


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


async def create_refresh_token(db: AsyncSession, refresh_token: RefreshToken) -> RefreshToken:
    db.add(refresh_token)
    await db.flush()
    await db.refresh(refresh_token)
    return refresh_token


async def get_refresh_token_by_jti(db: AsyncSession, jti: str) -> RefreshToken | None:
    from sqlalchemy import select
    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    return result.scalar_one_or_none()


async def delete_refresh_token(db: AsyncSession, refresh_token: RefreshToken) -> None:
    await db.delete(refresh_token)
    await db.flush()


async def delete_all_refresh_tokens_by_user_id(db: AsyncSession, user_id: int) -> None:
    from sqlalchemy import delete
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await db.flush()

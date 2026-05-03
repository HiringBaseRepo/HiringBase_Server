"""User management business logic."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.hashing import get_password_hash
from app.core.utils.pagination import PaginationParams
from app.features.models import User
from app.features.users.repositories.repository import list_users as list_users_query
from app.features.users.repositories.repository import save_user
from app.features.users.schemas.schema import CreateHRAccountRequest, UserCreatedResponse, UserListItem
from app.shared.enums.user_roles import UserRole
from app.shared.schemas.response import PaginatedResponse


async def create_hr_account(db: AsyncSession, data: CreateHRAccountRequest) -> UserCreatedResponse:
    user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        company_id=data.company_id,
        role=UserRole.HR,
    )
    user = await save_user(db, user)
    await db.commit()
    return UserCreatedResponse.model_validate(user)


async def list_users(
    db: AsyncSession,
    *,
    current_user: User,
    pagination: PaginationParams,
    company_id: int | None = None,
    role: UserRole | None = None,
    q: str | None = None,
) -> PaginatedResponse[UserListItem]:
    users, total = await list_users_query(
        db,
        pagination=pagination,
        current_user_role=current_user.role,
        current_user_company_id=current_user.company_id,
        company_id=company_id,
        role=role,
        q=q,
    )
    pages = (total + pagination.per_page - 1) // pagination.per_page
    return PaginatedResponse(
        data=[UserListItem.model_validate(user) for user in users],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=pages,
        has_next=pagination.page < pages,
        has_prev=pagination.page > 1,
    )

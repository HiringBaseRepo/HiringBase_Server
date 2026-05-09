"""User management business logic."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.hashing import get_password_hash
from app.core.utils.pagination import PaginationParams
from app.features.users.models import User
from app.features.users.repositories.repository import list_users as list_users_query, get_users_stats as get_users_stats_query, get_user_by_id, delete_user as delete_user_repo
from app.features.users.repositories.repository import save_user, update_user_repo
from app.features.users.schemas.schema import CreateHRAccountRequest, UserCreatedResponse, UserListItem, UpdateUserRequest
from app.shared.enums.user_roles import UserRole
from app.shared.schemas.response import PaginatedResponse
from app.features.audit_logs.models import AuditLog
from app.features.audit_logs.repositories.repository import create_audit_log


async def create_hr_account(
    db: AsyncSession, 
    data: CreateHRAccountRequest,
    *,
    current_user: User,
    ip_address: str | None = None
) -> UserCreatedResponse:
    user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        company_id=data.company_id,
        avatar_url=data.avatar_url,
        role=UserRole.HR,
    )
    user = await save_user(db, user)
    
    # Audit Log
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action="CREATE_HR_ACCOUNT",
            entity_type="user",
            entity_id=user.id,
            new_values=data.model_dump(exclude={"password"}),
            ip_address=ip_address,
        )
    )
    
    await db.commit()
    return UserCreatedResponse.model_validate(user)


async def list_users(
    db: AsyncSession,
    *,
    current_user: User,
    pagination: PaginationParams,
    company_id: int | None = None,
    role: UserRole | None = None,
    status: str | None = None,
    q: str | None = None,
) -> PaginatedResponse[UserListItem]:
    users, total = await list_users_query(
        db,
        pagination=pagination,
        current_user_role=current_user.role,
        current_user_company_id=current_user.company_id,
        company_id=company_id,
        role=role,
        status=status,
        q=q,
    )
    pages = (total + pagination.per_page - 1) // pagination.per_page
    
    data = []
    for user in users:
        item = UserListItem.model_validate(user)
        if user.company:
            item.company_name = user.company.name
        data.append(item)

    return PaginatedResponse(
        data=data,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        total_pages=pages,
        has_next=pagination.page < pages,
        has_prev=pagination.page > 1,
    )


async def get_users_stats(db: AsyncSession) -> dict:
    return await get_users_stats_query(db)


async def get_user(db: AsyncSession, user_id: int) -> UserListItem:
    user = await get_user_by_id(db, user_id)
    if not user:
        from app.core.exceptions import UserNotFoundException
        raise UserNotFoundException()
    
    item = UserListItem.model_validate(user)
    if user.company:
        item.company_name = user.company.name
    return item


async def update_user(
    db: AsyncSession, 
    user_id: int, 
    data: UpdateUserRequest,
    *,
    current_user: User,
    ip_address: str | None = None
) -> UserListItem:
    user = await get_user_by_id(db, user_id)
    if not user:
        from app.core.exceptions import UserNotFoundException
        raise UserNotFoundException()
    
    old_values = {
        "full_name": user.full_name,
        "is_active": user.is_active,
        "company_id": user.company_id,
        "avatar_url": user.avatar_url,
    }
    
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.company_id is not None:
        user.company_id = data.company_id
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url

    await update_user_repo(db, user)
    
    # Audit Log
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action="UPDATE_USER",
            entity_type="user",
            entity_id=user.id,
            old_values=old_values,
            new_values=data.model_dump(exclude_unset=True),
            ip_address=ip_address,
        )
    )
    
    await db.commit()
    return UserListItem.model_validate(user)


async def delete_user(
    db: AsyncSession, 
    user_id: int,
    *,
    current_user: User,
    ip_address: str | None = None
) -> None:
    user = await get_user_by_id(db, user_id)
    if not user:
        from app.core.exceptions import UserNotFoundException
        raise UserNotFoundException()
    
    await delete_user_repo(db, user)
    
    # Audit Log
    await create_audit_log(
        db,
        AuditLog(
            company_id=current_user.company_id,
            user_id=current_user.id,
            action="DELETE_USER",
            entity_type="user",
            entity_id=user_id,
            old_values={"email": user.email, "full_name": user.full_name},
            ip_address=ip_address,
        )
    )
    
    await db.commit()

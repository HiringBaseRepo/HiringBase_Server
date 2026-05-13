import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from app.core.database.base import engine  # noqa: E402
from app.features.models import User  # noqa: E402
from app.core.security.hashing import get_password_hash  # noqa: E402
from app.shared.enums.user_roles import UserRole  # noqa: E402

async def create_super_admin():
    print("========================================")
    print("🚀 HiringBase Super Admin Seeder")
    print("========================================")
    
    email = input("Enter Admin Email: ").strip()
    if not email:
        print("❌ Email is required")
        return

    import getpass
    password = getpass.getpass("Enter Admin Password: ").strip()
    if not password:
        print("❌ Password is required")
        return
        
    full_name = input("Enter Full Name: ").strip()
    if not full_name:
        print("❌ Full name is required")
        return

    async with AsyncSession(engine) as session:
        # Check if user already exists
        from sqlalchemy import select
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            print(f"❌ User with email {email} already exists.")
            return

        try:
            new_admin = User(
                email=email,
                full_name=full_name,
                password_hash=get_password_hash(password),
                role=UserRole.SUPER_ADMIN,
                is_active=True
            )
            session.add(new_admin)
            await session.commit()
            print(f"✅ Success! Super Admin '{email}' has been created.")
            print("You can now login via the web dashboard.")
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating admin: {e}")

if __name__ == "__main__":
    asyncio.run(create_super_admin())

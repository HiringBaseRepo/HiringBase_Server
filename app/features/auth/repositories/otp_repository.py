from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.auth.models import PasswordResetOtp


async def upsert_password_reset_otp(
    db: AsyncSession, user_id: int, otp_hash: str, expires_at: datetime
) -> PasswordResetOtp:
    """Hapus OTP lama untuk user ini, lalu simpan OTP baru (upsert-style)."""
    await db.execute(delete(PasswordResetOtp).where(PasswordResetOtp.user_id == user_id))
    
    otp_record = PasswordResetOtp(
        user_id=user_id, otp_hash=otp_hash, expires_at=expires_at
    )
    db.add(otp_record)
    await db.flush()
    await db.refresh(otp_record)
    return otp_record


async def find_password_reset_otp(
    db: AsyncSession, user_id: int, otp_hash: str
) -> PasswordResetOtp | None:
    """Cari record OTP berdasarkan user_id dan otp_hash."""
    result = await db.execute(
        select(PasswordResetOtp).where(
            PasswordResetOtp.user_id == user_id, PasswordResetOtp.otp_hash == otp_hash
        )
    )
    return result.scalar_one_or_none()


async def delete_password_reset_otp(db: AsyncSession, user_id: int) -> None:
    """Hapus OTP untuk user ini."""
    await db.execute(delete(PasswordResetOtp).where(PasswordResetOtp.user_id == user_id))
    await db.flush()

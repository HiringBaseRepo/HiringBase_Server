from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from app.core.config import settings
from pathlib import Path

# Mail configuration
mail_conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USER,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=settings.SMTP_FROM,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

async def send_email_async(
    subject: str,
    recipients: list[str],
    body: str,
    subtype: MessageType = MessageType.html
) -> None:
    """Send email asynchronously using FastMail."""
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype=subtype
    )
    
    fm = FastMail(mail_conf)
    await fm.send_message(message)

import smtplib
from email.message import EmailMessage

import anyio
import httpx
import structlog
from fastapi_mail import MessageType

from app.core.config import settings

logger = structlog.get_logger(__name__)
BREVO_SMTP_HOST = "smtp-relay.brevo.com"


async def send_email_async(
    subject: str,
    recipients: list[str],
    body: str,
    subtype: MessageType = MessageType.html,
) -> None:
    """Send email via Brevo HTTP API when available, with SMTP fallback."""
    if settings.BREVO_API_KEY:
        await _send_email_via_brevo_api(
            subject=subject,
            recipients=recipients,
            body=body,
            subtype=subtype,
        )
        return

    logger.warning(
        "brevo_api_key_missing_fallback_to_smtp",
        smtp_host=settings.SMTP_HOST,
        smtp_port=settings.SMTP_PORT,
    )
    await _send_email_via_smtp(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype=subtype,
    )


async def _send_email_via_brevo_api(
    *,
    subject: str,
    recipients: list[str],
    body: str,
    subtype: MessageType,
) -> None:
    sender_email = settings.SMTP_FROM
    if not sender_email:
        raise ValueError("SMTP_FROM must be configured for Brevo sender email")

    payload = {
        "sender": {
            "name": settings.APP_NAME,
            "email": sender_email,
        },
        "to": [{"email": recipient} for recipient in recipients],
        "subject": subject,
    }

    if subtype == MessageType.plain:
        payload["textContent"] = body
    else:
        payload["htmlContent"] = body

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.BREVO_API_BASE_URL}/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": settings.BREVO_API_KEY,
                "content-type": "application/json",
            },
            json=payload,
        )

    if response.status_code >= 400:
        logger.error(
            "brevo_api_send_failed",
            status_code=response.status_code,
            response=response.text,
        )
        response.raise_for_status()

    logger.info("brevo_api_email_sent", recipients=recipients, subject=subject)


async def _send_email_via_smtp(
    *,
    subject: str,
    recipients: list[str],
    body: str,
    subtype: MessageType,
) -> None:
    smtp_host = settings.SMTP_HOST
    smtp_user = settings.SMTP_USER
    smtp_password = settings.SMTP_PASSWORD
    sender_email = settings.SMTP_FROM

    if not smtp_host or not smtp_user or not smtp_password or not sender_email:
        raise ValueError("SMTP configuration incomplete")

    ports_to_try = [settings.SMTP_PORT]
    if smtp_host == BREVO_SMTP_HOST and settings.SMTP_PORT == 587:
        ports_to_try.append(2525)

    last_error: Exception | None = None
    for port in ports_to_try:
        try:
            await anyio.to_thread.run_sync(
                _send_email_sync_smtp,
                smtp_host,
                port,
                smtp_user,
                smtp_password,
                sender_email,
                subject,
                recipients,
                body,
                subtype,
            )
            logger.info("smtp_email_sent", recipients=recipients, subject=subject, port=port)
            return
        except Exception as exc:
            last_error = exc
            logger.warning(
                "smtp_send_attempt_failed",
                smtp_host=smtp_host,
                smtp_port=port,
                error=str(exc),
            )

    if last_error is not None:
        raise last_error


def _send_email_sync_smtp(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    sender_email: str,
    subject: str,
    recipients: list[str],
    body: str,
    subtype: MessageType,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = ", ".join(recipients)

    if subtype == MessageType.plain:
        message.set_content(body)
    else:
        message.set_content("This email requires an HTML-capable email client.")
        message.add_alternative(body, subtype="html")

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_password)
        server.send_message(message)

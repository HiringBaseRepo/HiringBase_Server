from app.core.tkq import broker
from app.core.utils.mailer import send_email_async
import structlog

logger = structlog.get_logger("mail_tasks")

@broker.task
async def send_ticket_email(email: str, name: str, ticket_number: str) -> None:
    """Send ticket confirmation email to applicant."""
    subject = f"Aplikasi Terkirim - {ticket_number}"
    body = f"""
    <html>
        <body>
            <h3>Halo {name},</h3>
            <p>Terima kasih telah melamar di HiringBase.</p>
            <p>Aplikasi Anda telah kami terima dengan nomor tiket: <strong>{ticket_number}</strong></p>
            <p>Gunakan nomor tiket ini untuk melacak status aplikasi Anda.</p>
            <br>
            <p>Salam,</p>
            <p>Tim HR</p>
        </body>
    </html>
    """
    try:
        await send_email_async(subject, [email], body)
        logger.info("ticket_email_sent", email=email, ticket=ticket_number)
    except Exception as e:
        logger.error("ticket_email_failed", email=email, ticket=ticket_number, error=str(e))
        raise e

@broker.task
async def send_interview_invite(
    email: str, 
    name: str, 
    job_title: str, 
    time: str, 
    location: str
) -> None:
    """Send interview invitation to applicant/HR."""
    subject = f"Undangan Interview - {job_title}"
    body = f"""
    <html>
        <body>
            <h3>Halo {name},</h3>
            <p>Kami mengundang Anda untuk mengikuti tahap wawancara untuk posisi <strong>{job_title}</strong>.</p>
            <p><strong>Detail Waktu:</strong> {time}</p>
            <p><strong>Lokasi/Link:</strong> {location}</p>
            <br>
            <p>Mohon konfirmasi kehadiran Anda.</p>
            <p>Salam,</p>
            <p>Tim HR</p>
        </body>
    </html>
    """
    try:
        await send_email_async(subject, [email], body)
        logger.info("interview_invite_sent", email=email, job=job_title)
    except Exception as e:
        logger.error("interview_invite_failed", email=email, job=job_title, error=str(e))
        raise e

"""Document upload business logic."""
from fastapi import UploadFile
from app.core.exceptions import (
    ApplicationNotFoundException,
    FileTooLargeException,
    InvalidFileTypeException,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.features.documents.repositories.repository import (
    get_application_for_company,
    save_document,
)
from app.features.documents.schemas.schema import DocumentUploadResponse
from app.features.applications.models import ApplicationDocument
from app.features.users.models import User
from app.shared.constants.storage import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, UPLOAD_PREFIX_PORTFOLIO, UPLOAD_PREFIX_DOCUMENT
from app.shared.enums.document_type import DocumentType
from app.shared.helpers.storage import build_public_url, generate_filename, get_s3_client


async def upload_document(
    db: AsyncSession,
    *,
    current_user: User,
    application_id: int,
    document_type: DocumentType,
    file: UploadFile,
) -> DocumentUploadResponse:
    application = await get_application_for_company(
        db,
        application_id=application_id,
        company_id=current_user.company_id,
    )
    if not application:
        raise ApplicationNotFoundException()

    ext = (file.filename or "").split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidFileTypeException()

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise FileTooLargeException()

    prefix = UPLOAD_PREFIX_PORTFOLIO if document_type == DocumentType.PORTFOLIO else UPLOAD_PREFIX_DOCUMENT
    key = generate_filename(file.filename, prefix)
    s3 = get_s3_client()
    s3.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=key,
        Body=content,
        ContentType=file.content_type or "application/pdf",
    )

    document = ApplicationDocument(
        application_id=application_id,
        document_type=document_type,
        file_name=file.filename,
        file_url=build_public_url(key),
        file_size=len(content),
        mime_type=file.content_type or "application/pdf",
    )
    document = await save_document(db, document)
    await db.commit()
    return DocumentUploadResponse(
        document_id=document.id,
        file_url=document.file_url,
        document_type=document_type.value,
    )

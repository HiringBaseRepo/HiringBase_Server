"""Document upload and management API."""
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database.base import get_db
from app.features.auth.dependencies import require_hr, get_current_user
from app.features.models import ApplicationDocument, Application, Job
from app.shared.schemas.response import StandardResponse
from app.shared.helpers.storage import generate_filename, get_s3_client, build_public_url
from app.shared.constants.storage import MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS
from app.shared.enums.document_type import DocumentType
from app.core.config import settings

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/{application_id}/upload", response_model=StandardResponse[dict])
async def upload_document(
    application_id: int,
    document_type: DocumentType,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await db.execute(select(Application).join(Job).where(
        Application.id == application_id,
        Job.company_id == current_user.company_id,
    ))
    application = result.scalar_one_or_none()
    if not application:
        return StandardResponse.error(message="Application not found", status_code=404)

    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return StandardResponse.error(message="Invalid file type")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        return StandardResponse.error(message="File too large")

    prefix = "cvs" if document_type == DocumentType.CV else "documents"
    key = generate_filename(file.filename, prefix)
    s3 = get_s3_client()
    s3.put_object(Bucket=settings.R2_BUCKET_NAME, Key=key, Body=content, ContentType=file.content_type or "application/pdf")

    doc = ApplicationDocument(
        application_id=application_id,
        document_type=document_type,
        file_name=file.filename,
        file_url=build_public_url(key),
        file_size=len(content),
        mime_type=file.content_type or "application/pdf",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return StandardResponse.ok(data={
        "document_id": doc.id,
        "file_url": doc.file_url,
        "document_type": document_type.value,
    })

"""Document upload and management API."""
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.base import get_db
from app.features.auth.dependencies.auth import require_hr
from app.features.documents.schemas.schema import DocumentUploadResponse
from app.features.documents.services.service import upload_document as upload_document_service
from app.shared.schemas.response import StandardResponse
from app.shared.enums.document_type import DocumentType

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/{application_id}/upload", response_model=StandardResponse[DocumentUploadResponse])
async def upload_document(
    application_id: int,
    document_type: DocumentType,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_hr),
):
    result = await upload_document_service(
        db,
        current_user=current_user,
        application_id=application_id,
        document_type=document_type,
        file=file,
    )
    return StandardResponse.ok(data=result)

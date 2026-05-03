"""Document schemas."""
from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: int
    file_url: str
    document_type: str

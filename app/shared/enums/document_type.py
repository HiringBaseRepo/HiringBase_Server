"""Applicant document types."""
from enum import Enum


class DocumentType(str, Enum):
    IJAZAH = "ijazah"
    KTP = "ktp"
    SKCK = "skck"
    SURAT_SEHAT = "surat_sehat"
    SERTIFIKAT = "sertifikat"
    PORTFOLIO = "portfolio"
    LAINNYA = "lainnya"

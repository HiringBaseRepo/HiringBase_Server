"""Applicant document types."""
from enum import Enum


class DocumentType(str, Enum):
    DEGREE = "degree"
    IDENTITY_CARD = "identity_card"
    CRIMINAL_RECORD = "criminal_record"
    HEALTH_CERTIFICATE = "health_certificate"
    CERTIFICATE = "certificate"
    PORTFOLIO = "portfolio"
    OTHERS = "others"

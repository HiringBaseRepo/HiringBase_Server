"""
Localization helpers for translating English internal Enums to Indonesian display names.
Strategy: English Core, Localized Presentation.
"""

from typing import Dict, Any
from app.shared.enums.document_type import DocumentType
from app.shared.enums.application_status import ApplicationStatus
from app.shared.enums.employment_type import EmploymentType
from app.shared.enums.user_roles import UserRole
from app.shared.enums.job_status import JobStatus
from app.shared.enums.ticket_status import TicketStatus
from app.shared.enums.field_type import FormFieldType
from app.shared.constants import audit_actions
from app.shared.constants.errors import (
    ERR_AI_CONNECTION,
    ERR_AI_SERVER,
    ERR_APPLICATION_NOT_FOUND,
    ERR_COMPANY_NAME_REQUIRED,
    ERR_COMPANY_NOT_FOUND,
    ERR_DUPLICATE_APPLICATION,
    ERR_FIELD_NOT_FOUND,
    ERR_FILE_TOO_LARGE,
    ERR_INTERVIEW_NOT_FOUND,
    ERR_INVALID_CREDENTIALS,
    ERR_INVALID_FILE_TYPE,
    ERR_INVALID_REFRESH_TOKEN,
    ERR_INVALID_SETUP_TOKEN,
    ERR_JOB_NOT_FOUND,
    ERR_MISSING_DOCUMENTS,
    ERR_PASSWORD_RESET_TOKEN_INVALID,
    ERR_REFRESH_TOKEN_EXPIRED,
    ERR_RULE_NOT_FOUND,
    ERR_SCORING_TEMPLATE_MISSING,
    ERR_SECURITY_ALERT,
    ERR_TICKET_NOT_FOUND,
    ERR_TOKEN_REVOKED,
    ERR_TOKEN_ROTATION_FAILED,
    ERR_UNAUTHENTICATED,
    ERR_UNAUTHORIZED,
    ERR_USER_INACTIVE,
    ERR_USER_NOT_FOUND,
    ERR_INVALID_KNOCKOUT_OPERATOR,
    ERR_FIELD_REQUIRED,
    ERR_OTHERS_UPLOAD_NOT_ALLOWED,
    ERR_SESSION_EXPIRED,
    ERR_INVALID_TOKEN,
    ERR_INVALID_UPLOAD_KEY,
    ERR_REFRESH_TOKEN_NOT_FOUND,
    ERR_INVALID_REQUEST_ORIGIN,
    ERR_TOKEN_INVALID_STRUCTURE,
    ERR_TOKEN_MISSING_SUB,
    ERR_TOKEN_INVALID_SUB,
    ERR_TOKEN_REUSED_ALERT,
    ERR_CANDIDATE_SCORE_NOT_FOUND,
    MSG_SCREENING_QUEUED,
)
from app.shared.constants.scoring import (
    ADMINISTRATIVE_WEIGHT_KEY,
    EDUCATION_WEIGHT_KEY,
    EXPERIENCE_WEIGHT_KEY,
    PORTFOLIO_WEIGHT_KEY,
    SKILL_MATCH_WEIGHT_KEY,
    SOFT_SKILL_WEIGHT_KEY,
)

# Mappings
DOCUMENT_TYPE_LABELS: Dict[DocumentType, str] = {
    DocumentType.IDENTITY_CARD: "KTP",
    DocumentType.DEGREE: "Ijazah",
    DocumentType.CRIMINAL_RECORD: "SKCK",
    DocumentType.HEALTH_CERTIFICATE: "Surat Keterangan Sehat",
    DocumentType.CERTIFICATE: "Sertifikat",
    DocumentType.PORTFOLIO: "Portofolio",
    DocumentType.OTHERS: "Dokumen Lainnya",
}

APPLICATION_STATUS_LABELS: Dict[ApplicationStatus, str] = {
    ApplicationStatus.APPLIED: "Dilamar",
    ApplicationStatus.DOC_CHECK: "Verifikasi Dokumen",
    ApplicationStatus.DOC_FAILED: "Dokumen Tidak Lengkap",
    ApplicationStatus.AI_PROCESSING: "Diproses AI",
    ApplicationStatus.AI_PASSED: "Lolos AI",
    ApplicationStatus.UNDER_REVIEW: "Dalam Review",
    ApplicationStatus.INTERVIEW: "Wawancara",
    ApplicationStatus.OFFERED: "Penawaran",
    ApplicationStatus.HIRED: "Diterima",
    ApplicationStatus.REJECTED: "Ditolak",
    ApplicationStatus.KNOCKOUT: "Gugur Kualifikasi",
}

EMPLOYMENT_TYPE_LABELS: Dict[EmploymentType, str] = {
    EmploymentType.FULL_TIME: "Penuh Waktu (Full-time)",
    EmploymentType.PART_TIME: "Paruh Waktu (Part-time)",
    EmploymentType.CONTRACT: "Kontrak",
    EmploymentType.INTERN: "Magang",
    EmploymentType.FREELANCE: "Lepas Waktu (Freelance)",
}

USER_ROLE_LABELS: Dict[UserRole, str] = {
    UserRole.SUPER_ADMIN: "Administrator Utama",
    UserRole.HR: "HR / Rekrutmen",
    UserRole.APPLICANT: "Pelamar",
}

JOB_STATUS_LABELS: Dict[JobStatus, str] = {
    JobStatus.DRAFT: "Draft",
    JobStatus.PUBLISHED: "Diterbitkan",
    JobStatus.CLOSED: "Ditutup",
    JobStatus.SCHEDULED: "Terjadwal",
}

TICKET_STATUS_LABELS: Dict[TicketStatus, str] = {
    TicketStatus.OPEN: "Terbuka",
    TicketStatus.IN_PROGRESS: "Sedang Diproses",
    TicketStatus.RESOLVED: "Selesai",
    TicketStatus.CLOSED: "Ditutup",
}

FIELD_TYPE_LABELS: Dict[FormFieldType, str] = {
    FormFieldType.TEXT: "Teks Pendek",
    FormFieldType.TEXTAREA: "Teks Panjang",
    FormFieldType.NUMBER: "Angka",
    FormFieldType.SELECT: "Pilihan Dropdown",
    FormFieldType.RADIO: "Pilihan Tunggal",
    FormFieldType.CHECKBOX: "Pilihan Ganda",
    FormFieldType.DATE: "Tanggal",
    FormFieldType.URL: "Link/URL",
    FormFieldType.FILE: "Unggah File",
}

SCORING_WEIGHT_LABELS: Dict[str, str] = {
    SKILL_MATCH_WEIGHT_KEY: "Kesesuaian Skill",
    EXPERIENCE_WEIGHT_KEY: "Pengalaman Kerja",
    EDUCATION_WEIGHT_KEY: "Pendidikan",
    PORTFOLIO_WEIGHT_KEY: "Portofolio",
    SOFT_SKILL_WEIGHT_KEY: "Soft Skills",
    ADMINISTRATIVE_WEIGHT_KEY: "Kelengkapan Admin",
}

AUDIT_ACTION_LABELS: Dict[str, str] = {
    audit_actions.LOGIN_FAILURE: "Login Gagal",
    audit_actions.LOGIN_SUCCESS: "Login Berhasil",
    audit_actions.PASSWORD_RESET_REQUESTED: "Meminta Reset Kata Sandi",
    audit_actions.LOGOUT: "Keluar dari Sistem",
    audit_actions.CREATE_HR_ACCOUNT: "Membuat Akun HR",
    audit_actions.UPDATE_USER: "Memperbarui Pengguna",
    audit_actions.DELETE_USER: "Menghapus Pengguna",
    audit_actions.CREATE_COMPANY: "Membuat Perusahaan",
    audit_actions.UPDATE_COMPANY: "Memperbarui Perusahaan",
    audit_actions.COMPANY_SUSPEND: "Menangguhkan Perusahaan",
    audit_actions.COMPANY_ACTIVATE: "Mengaktifkan Perusahaan",
    audit_actions.JOB_CREATE: "Membuat Lowongan",
    audit_actions.JOB_REQUIREMENTS_UPDATE: "Memperbarui Persyaratan Lowongan",
    audit_actions.JOB_FORM_UPDATE: "Memperbarui Form Lowongan",
    audit_actions.JOB_PUBLISH: "Menerbitkan Lowongan",
    audit_actions.JOB_CLOSE: "Menutup Lowongan",
    audit_actions.JOB_FORM_FIELD_CREATE: "Membuat Field Form Lowongan",
    audit_actions.JOB_FORM_FIELD_UPDATE: "Memperbarui Field Form Lowongan",
    audit_actions.JOB_FORM_FIELD_DELETE: "Menghapus Field Form Lowongan",
    audit_actions.JOB_FORM_FIELD_REORDER: "Mengurutkan Ulang Field Form Lowongan",
    audit_actions.APPLICATION_SUBMIT: "Menerima Lamaran",
    audit_actions.APPLICATION_STATUS_UPDATE: "Mengubah Status Lamaran",
    audit_actions.INTERVIEW_SCHEDULE: "Menjadwalkan Wawancara",
    audit_actions.SCORING_TEMPLATE_CREATE: "Membuat Template Skoring",
    audit_actions.SCORING_TEMPLATE_UPDATE: "Memperbarui Template Skoring",
    audit_actions.AUTOMATED_SCREENING_CREATE: "Membuat Hasil Screening Otomatis",
    audit_actions.AUTOMATED_SCREENING_UPDATE: "Memperbarui Hasil Screening Otomatis",
    audit_actions.AUTOMATED_SCREENING_FALLBACK: "Mengalihkan Screening ke Review Manual",
    audit_actions.MANUAL_OVERRIDE_SCORE: "Melakukan Override Skor Manual",
    audit_actions.NOTIFICATION_MARK_READ: "Menandai Notifikasi Sudah Dibaca",
    audit_actions.NOTIFICATION_MARK_READ_ALL: "Menandai Semua Notifikasi Sudah Dibaca",
}


INTERNAL_MESSAGES: Dict[str, str] = {
    # Auth
    "Login successful": "Login berhasil",
    "Logout successful": "Logout berhasil",
    "Logged out": "Anda telah keluar dari sistem",
    "Token refreshed": "Sesi berhasil diperbarui",
    "Super admin registered": "Administrator utama berhasil didaftarkan",
    "HR and company registered": "HR dan Perusahaan berhasil didaftarkan",
    
    # Jobs & Applications
    "Step 1 saved": "Langkah 1 berhasil disimpan",
    "Application submitted successfully": "Lamaran Anda berhasil dikirim",
    
    # Screening
    "Screening started in background": "Proses screening telah dimulai di latar belakang",
    "Screening completed": "Proses screening selesai",
    "Proses screening telah dimasukkan dalam antrean": "Proses screening telah dimasukkan dalam antrean",
    "screening_completed_reason": "Screening AI selesai. Skor akhir: {score}",
    "screening_already_queued": "Screening sudah ada dalam antrean atau sedang diproses",
    "screening_pending_quota": "Screening ditunda sementara karena batas kuota atau concurrency aktif",
    "screening_fallback_under_review": "Screening AI dialihkan ke review manual karena proses otomatis gagal",
    "screening_recovery_retry_reason": "Screening diproses ulang setelah status sebelumnya terdeteksi macet",
    "screening_quota_deferred_reason": "Screening ditunda otomatis karena guard kuota aktif",
    
    # Validators
    "Validator skipped (no API key)": "Validasi dilewati (API Key tidak dikonfigurasi)",
    "OCR text is too short or unreadable": "Teks dokumen tidak terbaca atau terlalu pendek",
    "API Error (Fallback to Pass)": "Kesalahan API (Dilewati otomatis)",
    "Internal validator error": "Kesalahan internal pada sistem validasi",
}

ERROR_MESSAGES: Dict[str, str] = {
    ERR_RULE_NOT_FOUND: "Aturan knockout tidak ditemukan",
    ERR_APPLICATION_NOT_FOUND: "Lamaran tidak ditemukan",
    ERR_JOB_NOT_FOUND: "Lowongan tidak ditemukan",
    ERR_USER_NOT_FOUND: "Pengguna tidak ditemukan",
    ERR_INVALID_CREDENTIALS: "Email atau password salah",
    ERR_USER_INACTIVE: "Akun tidak aktif",
    ERR_INVALID_REFRESH_TOKEN: "Refresh token tidak valid",
    ERR_REFRESH_TOKEN_EXPIRED: "Sesi telah berakhir, silakan login kembali",
    ERR_TOKEN_REVOKED: "Token telah dicabut atau sudah digunakan",
    ERR_SECURITY_ALERT: "Peringatan Keamanan: Silakan login kembali",
    ERR_INVALID_FILE_TYPE: "Format file tidak didukung",
    ERR_FILE_TOO_LARGE: "Ukuran file terlalu besar",
    ERR_PASSWORD_RESET_TOKEN_INVALID: "Token reset password tidak valid atau sudah kedaluwarsa",
    ERR_INVALID_SETUP_TOKEN: "Setup token tidak valid atau belum diatur di .env",
    ERR_COMPANY_NAME_REQUIRED: "Nama perusahaan wajib diisi untuk HR",
    ERR_MISSING_DOCUMENTS: "Dokumen wajib belum diunggah",
    ERR_TOKEN_ROTATION_FAILED: "Gagal memperbarui sesi (token rotation)",
    ERR_DUPLICATE_APPLICATION: "Anda sudah melamar untuk lowongan ini",
    ERR_TICKET_NOT_FOUND: "Tiket tidak ditemukan",
    ERR_SCORING_TEMPLATE_MISSING: "Template penilaian tidak ditemukan",
    ERR_INTERVIEW_NOT_FOUND: "Wawancara tidak ditemukan",
    ERR_COMPANY_NOT_FOUND: "Perusahaan tidak ditemukan",
    ERR_FIELD_NOT_FOUND: "Field tidak ditemukan",
    ERR_AI_CONNECTION: "Gagal terhubung ke API AI (Timeout/Network)",
    ERR_AI_SERVER: "Server API AI sedang bermasalah (5xx)",
    ERR_UNAUTHENTICATED: "Otentikasi diperlukan",
    ERR_UNAUTHORIZED: "Anda tidak memiliki akses untuk melakukan tindakan ini",
    ERR_INVALID_KNOCKOUT_OPERATOR: "Operator knockout tidak valid: {operator}",
    ERR_FIELD_REQUIRED: "Field '{field}' wajib diisi",
    ERR_OTHERS_UPLOAD_NOT_ALLOWED: "Upload dokumen dengan tipe OTHERS tidak diizinkan untuk lowongan ini",
    ERR_SESSION_EXPIRED: "Sesi telah berakhir, silakan login kembali",
    ERR_INVALID_TOKEN: "Token tidak valid atau kedaluwarsa",
    ERR_INVALID_UPLOAD_KEY: "Tipe dokumen tidak dikenali untuk key upload: {key}",
    ERR_REFRESH_TOKEN_NOT_FOUND: "Refresh token tidak ditemukan di cookies",
    ERR_INVALID_REQUEST_ORIGIN: "Permintaan lintas origin tidak diizinkan untuk endpoint sesi ini",
    ERR_TOKEN_INVALID_STRUCTURE: "Struktur token tidak valid",
    ERR_TOKEN_MISSING_SUB: "Token tidak memiliki identitas pengguna",
    ERR_TOKEN_INVALID_SUB: "Identitas pengguna tidak valid",
    ERR_TOKEN_REUSED_ALERT: "Peringatan Keamanan: Token telah digunakan. Sesi Anda dihentikan demi keamanan.",
    ERR_CANDIDATE_SCORE_NOT_FOUND: "Skor kandidat tidak ditemukan",
    MSG_SCREENING_QUEUED: "Proses screening telah dimasukkan dalam antrean",
}


def get_label(enum_value: Any, **kwargs) -> str:
    """Get Indonesian label for a given Enum or internal key."""
    label = _get_raw_label(enum_value)
    
    if kwargs:
        try:
            return label.format(**kwargs)
        except (KeyError, ValueError):
            return label
    return label


def _get_raw_label(enum_value: Any) -> str:
    """Internal helper to get raw label string."""
    if isinstance(enum_value, DocumentType):
        return DOCUMENT_TYPE_LABELS.get(enum_value, str(enum_value))
    if isinstance(enum_value, ApplicationStatus):
        return APPLICATION_STATUS_LABELS.get(enum_value, str(enum_value))
    if isinstance(enum_value, EmploymentType):
        return EMPLOYMENT_TYPE_LABELS.get(enum_value, str(enum_value))
    if isinstance(enum_value, UserRole):
        return USER_ROLE_LABELS.get(enum_value, str(enum_value))
    if isinstance(enum_value, JobStatus):
        return JOB_STATUS_LABELS.get(enum_value, str(enum_value))
    if isinstance(enum_value, TicketStatus):
        return TICKET_STATUS_LABELS.get(enum_value, str(enum_value))
    if isinstance(enum_value, FormFieldType):
        return FIELD_TYPE_LABELS.get(enum_value, str(enum_value))
    
    # Handle string keys (weights, audit actions, messages)
    if enum_value in SCORING_WEIGHT_LABELS:
        return SCORING_WEIGHT_LABELS[enum_value]
    if enum_value in AUDIT_ACTION_LABELS:
        return AUDIT_ACTION_LABELS[enum_value]
    if enum_value in INTERNAL_MESSAGES:
        return INTERNAL_MESSAGES[enum_value]
    if enum_value in ERROR_MESSAGES:
        return ERROR_MESSAGES[enum_value]
    
    return str(enum_value)

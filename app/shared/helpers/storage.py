"""Cloudflare R2 / S3 compatible storage helper."""
import uuid

import anyio
import boto3
from botocore.config import Config

from app.core.config import settings

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def generate_filename(original: str, prefix: str) -> str:
    ext = original.split(".")[-1] if "." in original else "bin"
    return f"{prefix}/{uuid.uuid4().hex}.{ext}"


def build_public_url(key: str) -> str:
    base = settings.R2_PUBLIC_URL or settings.R2_ENDPOINT_URL
    return f"{base}/{key}"


def upload_file(content: bytes, key: str, content_type: str = "application/pdf") -> str:
    """Upload content to R2 and return the public URL."""
    s3 = get_s3_client()
    s3.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=key,
        Body=content,
        ContentType=content_type,
        CacheControl="public, max-age=31536000, immutable",
    )
    return build_public_url(key)


async def upload_file_async(
    content: bytes, key: str, content_type: str = "application/pdf"
) -> str:
    """Async wrapper around boto3 upload to avoid blocking event loop."""
    return await anyio.to_thread.run_sync(
        upload_file,
        content,
        key,
        content_type,
    )


def delete_file(key: str) -> None:
    s3 = get_s3_client()
    s3.delete_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=key,
    )


async def delete_file_async(key: str) -> None:
    await anyio.to_thread.run_sync(delete_file, key)

"""Storage helpers for local and S3/R2-compatible file handling."""

from __future__ import annotations

from pathlib import Path

from config import get_config


def storage_provider() -> str:
    """Return configured storage provider."""
    return str(get_config("storage.provider", "local")).strip().lower()


def signed_download_url(path: str, expires_in: int | None = None) -> str:
    """Return a signed URL for S3/R2 files or the local path for local storage."""
    provider = storage_provider()
    if provider == "local":
        return path
    if provider not in {"s3", "r2"}:
        raise RuntimeError(f"Unsupported storage provider: {provider}")
    import boto3

    bucket = str(get_config("storage.s3_bucket", ""))
    if not bucket:
        raise RuntimeError("storage.s3_bucket is required for S3/R2 signed URLs")
    client = boto3.client(
        "s3",
        endpoint_url=str(get_config("storage.s3_endpoint_url", "")) or None,
        aws_access_key_id=str(get_config("storage.s3_access_key_id", "")) or None,
        aws_secret_access_key=str(get_config("storage.s3_secret_access_key", "")) or None,
    )
    key = Path(path).as_posix().lstrip("/")
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=int(expires_in or get_config("storage.signed_url_expiry_seconds", 900)),
    )

"""
CleanTrack AI — S3-Compatible Object Storage (MinIO/AWS S3)
Handles photo compression, thumbnail generation, and presigned URL creation.
"""
import io
import uuid
from typing import Optional, Tuple

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from PIL import Image

from app.core.config import get_settings

settings = get_settings()

# ── S3 Client ─────────────────────────────────────────────────────────────────
_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name=settings.storage_region,
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "adaptive"},
            ),
        )
    return _s3_client


# ── Photo processing ──────────────────────────────────────────────────────────
PHOTO_MAX_SIZE = (1920, 1080)
THUMB_SIZE = (320, 240)
PHOTO_QUALITY = 85
THUMB_QUALITY = 75


def _compress_image(image_bytes: bytes, max_size: Tuple[int, int], quality: int) -> bytes:
    """Compress and resize an image, converting to JPEG."""
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("RGB")
    img.thumbnail(max_size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    buf.seek(0)
    return buf.read()


async def upload_report_photo(
    file_bytes: bytes,
    report_id: str,
    original_filename: str,
) -> Tuple[str, str]:
    """
    Compress photo + generate thumbnail. Upload both to MinIO.
    Returns (photo_key, thumbnail_key).
    """
    base_key = f"reports/{report_id}/{uuid.uuid4().hex}"

    # Compress main photo
    compressed = _compress_image(file_bytes, PHOTO_MAX_SIZE, PHOTO_QUALITY)
    photo_key = f"{base_key}.jpg"

    # Generate thumbnail
    thumbnail = _compress_image(file_bytes, THUMB_SIZE, THUMB_QUALITY)
    thumb_key = f"thumbs/{report_id}/{uuid.uuid4().hex}_thumb.jpg"

    s3 = get_s3_client()

    # Upload compressed photo
    s3.put_object(
        Bucket=settings.storage_bucket_photos,
        Key=photo_key,
        Body=compressed,
        ContentType="image/jpeg",
        Metadata={"report_id": report_id, "original_name": original_filename},
    )

    # Upload thumbnail
    s3.put_object(
        Bucket=settings.storage_bucket_thumbs,
        Key=thumb_key,
        Body=thumbnail,
        ContentType="image/jpeg",
    )

    return photo_key, thumb_key


async def upload_dispatch_photo(
    file_bytes: bytes,
    dispatch_id: str,
    photo_type: str,  # "before" | "after"
) -> str:
    """Upload before/after dispatch proof photo. Returns S3 key."""
    compressed = _compress_image(file_bytes, PHOTO_MAX_SIZE, PHOTO_QUALITY)
    key = f"dispatch/{dispatch_id}/{photo_type}_{uuid.uuid4().hex}.jpg"

    get_s3_client().put_object(
        Bucket=settings.storage_bucket_photos,
        Key=key,
        Body=compressed,
        ContentType="image/jpeg",
    )
    return key


def get_photo_url(key: str, bucket: Optional[str] = None) -> str:
    """Return public URL for a stored object."""
    bucket = bucket or settings.storage_bucket_photos
    return f"{settings.storage_endpoint_url}/{bucket}/{key}"


def generate_presigned_upload_url(report_id: str, filename: str, expires: int = 300) -> str:
    """Generate a presigned PUT URL so the mobile client can upload directly."""
    key = f"reports/{report_id}/raw_{uuid.uuid4().hex}_{filename}"
    url = get_s3_client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.storage_bucket_photos,
            "Key": key,
            "ContentType": "image/jpeg",
        },
        ExpiresIn=expires,
    )
    return url, key

from minio import Minio

from app.config import settings

minio_client = Minio(
    endpoint=settings.minio_endpoint,
    access_key=settings.minio_root_user,
    secret_key=settings.minio_root_password,
    secure=settings.minio_secure,
)

_bucket = settings.minio_bucket


async def check_bucket() -> None:
    if not minio_client.bucket_exists(_bucket):
        minio_client.make_bucket(_bucket)


async def upload_file(file_path: str, data: bytes, content_type: str) -> None:
    minio_client.put_object(
        bucket_name=_bucket,
        object_name=file_path,
        data=data,
        length=len(data),
        content_type=content_type,
    )


async def get_presigned_url(object_name: str, expires: int = 1800) -> str:
    return minio_client.presigned_get_object(
        bucket_name=_bucket,
        object_name=object_name,
        expires=expires,
    )

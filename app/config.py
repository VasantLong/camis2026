from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # PostgreSQL — 生产环境通过 .env 覆盖
    postgres_user: str = "docapp"
    postgres_password: str = "secret_pg_pwd"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "doc_metadata"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # MinIO — 生产环境通过 .env 覆盖
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket: str = "company-docs"
    minio_secure: bool = False

    # Redis — 生产环境通过 .env 覆盖
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = "secret_redis_pwd"
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # SMTP (Mailpit for dev)
    smtp_host: str = "localhost"
    smtp_port: int = 11025
    smtp_from: str = "noreply@camis.local"

    # JWT — 生产环境必须覆盖
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_must_be_set(cls, v: str) -> str:
        if not v:
            raise ValueError("JWT_SECRET 必须设置，请在 .env 中配置")
        return v

    # CORS
    allow_origins: str = "http://localhost:5173"


settings = Settings()

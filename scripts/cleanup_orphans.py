"""扫描并清理 MinIO 中存在但 documents 表中无对应记录的孤儿文件。

用法:
    # 预览（不删除）
    python scripts/cleanup_orphans.py --dry-run

    # 实际删除（跳过 1 小时内上传的文件）
    python scripts/cleanup_orphans.py --no-dry-run --min-age-hours 1
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timezone

from app.database import async_session
from app.models.document import Document
from sqlalchemy import select

from app.config import settings
from minio import Minio

logger = logging.getLogger("camis.orphan-cleaner")


async def cleanup_orphans(dry_run: bool = True, min_age_hours: int = 1) -> int:
    minio = Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )
    bucket = settings.minio_bucket

    # 1. 从 DB 收集所有已知 minio_path
    async with async_session() as db:
        result = await db.execute(select(Document.minio_path))
        db_paths: set[str] = {row[0] for row in result.all()}

    logger.info("DB documents count: %d", len(db_paths))

    # 2. 遍历 MinIO，找出孤儿
    now = datetime.now(timezone.utc)
    orphans: list[str] = []
    scanned = 0

    for obj in minio.list_objects(bucket, recursive=True):
        scanned += 1
        path = obj.object_name
        if path in db_paths:
            continue
        age_hours = (now - obj.last_modified).total_seconds() / 3600
        if age_hours < min_age_hours:
            logger.debug("skip recent: %s (%.1fh old)", path, age_hours)
            continue
        orphans.append(path)

    logger.info("Scanned %d objects, orphans: %d", scanned, len(orphans))

    # 3. 清理
    deleted = 0
    for path in orphans:
        if dry_run:
            logger.info("DRY-RUN would delete: %s", path)
        else:
            minio.remove_object(bucket, path)
            logger.info("deleted: %s", path)
        deleted += 1

    return deleted


def main():
    parser = argparse.ArgumentParser(description="MinIO orphan file cleaner")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Preview only, do not delete (default)")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false",
                        help="Actually delete orphan files")
    parser.add_argument("--min-age-hours", type=float, default=1.0,
                        help="Skip files uploaded within N hours (default: 1)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    deleted = asyncio.run(cleanup_orphans(dry_run=args.dry_run,
                                           min_age_hours=args.min_age_hours))
    print(f"\nDone. {'Would delete' if args.dry_run else 'Deleted'} {deleted} orphan(s).")


if __name__ == "__main__":
    main()

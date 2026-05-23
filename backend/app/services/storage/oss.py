"""OSS object storage wrapper (architecture.md §11).

MVP note: raw document text can live in a DB column, so the pipeline does not
depend on OSS yet. This wrapper is scaffolded for web snapshots / exports.
"""
from __future__ import annotations

from loguru import logger

from app.core.config import settings


class OSSStorage:
    """Thin wrapper over Aliyun OSS — used for large files, not structured data."""

    def __init__(self) -> None:
        self._bucket = None  # lazy init

    @property
    def is_configured(self) -> bool:
        return bool(settings.OSS_ACCESS_KEY_ID and settings.OSS_ENDPOINT)

    @property
    def bucket(self):
        if not self.is_configured:
            raise RuntimeError("OSS is not configured — set OSS_* in backend/.env")
        if self._bucket is None:
            import oss2  # imported lazily so the app boots without OSS configured

            auth = oss2.Auth(
                settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET
            )
            self._bucket = oss2.Bucket(
                auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET
            )
        return self._bucket

    def save_text(self, path: str, content: str) -> str:
        """Save text content; return the oss_path. architecture.md §11."""
        self.bucket.put_object(path, content.encode("utf-8"))
        logger.info(f"OSS saved: {path}")
        return path

    def get_signed_url(self, path: str, expires: int = 3600) -> str:
        """Return a temporary signed URL for a private object."""
        return self.bucket.sign_url("GET", path, expires)


_storage: OSSStorage | None = None


def get_storage() -> OSSStorage:
    """Module-level singleton accessor."""
    global _storage
    if _storage is None:
        _storage = OSSStorage()
    return _storage

"""Object storage — Aliyun OSS wrapper (architecture.md §11)."""
from app.services.storage.oss import OSSStorage, get_storage

__all__ = ["OSSStorage", "get_storage"]

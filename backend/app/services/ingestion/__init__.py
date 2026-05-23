"""Ingestion — stages 1-2: collect public information, then clean & dedup."""
from app.services.ingestion.clean import clean_documents
from app.services.ingestion.providers import collect_documents, load_seed_documents

__all__ = ["collect_documents", "load_seed_documents", "clean_documents"]

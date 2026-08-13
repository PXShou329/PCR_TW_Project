"""Deterministic private-workbook staging extraction.

This package does not write the research CSV SSOT or the serving database.
"""

from .catalog import (
    CatalogMergeError,
    LocalCatalog,
    export_staging_media,
    merge_staging_catalog_files,
    merge_staging_catalogs,
)
from .deep_1_7 import extract_deep_1_7_workbook
from .models import WorkbookExtract, WorkbookLayoutError
from .portrait_review import (
    PortraitReviewError,
    build_materialization_manifest,
    build_portrait_review_queue,
    materialize_character_catalog,
    validate_override_registry,
    verify_evidence_files,
)
from .workbook_2 import extract_workbook_2

__all__ = [
    "CatalogMergeError",
    "LocalCatalog",
    "PortraitReviewError",
    "WorkbookExtract",
    "WorkbookLayoutError",
    "export_staging_media",
    "build_materialization_manifest",
    "build_portrait_review_queue",
    "extract_deep_1_7_workbook",
    "extract_workbook_2",
    "merge_staging_catalog_files",
    "merge_staging_catalogs",
    "materialize_character_catalog",
    "validate_override_registry",
    "verify_evidence_files",
]

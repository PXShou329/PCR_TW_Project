"""Deterministic, fail-closed ingestion for user-supplied Gacha forecasts."""

from .docx import (
    CANDIDATE_SCHEMA_VERSION,
    GachaDocxError,
    canonical_json_bytes,
    extract_gacha_forecast_docx,
)

__all__ = [
    "CANDIDATE_SCHEMA_VERSION",
    "GachaDocxError",
    "canonical_json_bytes",
    "extract_gacha_forecast_docx",
]

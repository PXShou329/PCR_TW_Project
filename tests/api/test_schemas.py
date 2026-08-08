from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from pcr_api.schemas import SourceMeta


VALID_SOURCE = {
    "canonical_source": "research_core_file_ssot",
    "fixture_sha256": "a" * 64,
    "import_run_id": "00000000-0000-4000-8000-000000000001",
    "revision_id": "a" * 64,
    "imported_at": "2026-08-08T00:00:00Z",
    "research_core_version": "v1.5",
    "raw_tree_sha256": "a" * 64,
    "semantic_tree_sha256": "b" * 64,
    "materialization_sha256": "c" * 64,
}


def test_source_meta_requires_uuid_and_lowercase_sha256_provenance() -> None:
    source = SourceMeta.model_validate(VALID_SOURCE)
    assert str(source.import_run_id) == VALID_SOURCE["import_run_id"]

    for field, invalid in (
        ("fixture_sha256", "short"),
        ("revision_id", "A" * 64),
        ("raw_tree_sha256", "g" * 64),
        ("semantic_tree_sha256", "0" * 63),
        ("materialization_sha256", "0" * 65),
        ("import_run_id", "not-a-uuid"),
    ):
        payload = deepcopy(VALID_SOURCE)
        payload[field] = invalid
        with pytest.raises(ValidationError):
            SourceMeta.model_validate(payload)

from __future__ import annotations

import pytest

from pcr_database.provision_roles import _required_secret


@pytest.mark.parametrize("value", ["", "short", "replace-me-now-please", "placeholder-secret-value"])
def test_service_role_passwords_fail_closed(monkeypatch, value: str) -> None:
    monkeypatch.setenv("PCR_API_DB_PASSWORD", value)
    with pytest.raises(RuntimeError, match="non-placeholder secret"):
        _required_secret("PCR_API_DB_PASSWORD")


def test_service_role_password_accepts_non_placeholder_secret(monkeypatch) -> None:
    monkeypatch.setenv("PCR_API_DB_PASSWORD", "test-only-strong-value-123")
    assert _required_secret("PCR_API_DB_PASSWORD") == "test-only-strong-value-123"

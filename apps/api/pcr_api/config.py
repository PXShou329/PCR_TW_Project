from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    application_version: str = "3.0.0-a5"
    api_version: str = "v1"
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )

    @classmethod
    def from_environment(cls) -> "Settings":
        database_url = os.getenv("PCR_DATABASE_URL", "").strip()
        if not database_url:
            raise RuntimeError("PCR_DATABASE_URL is required")
        configured_origins = tuple(
            value.strip()
            for value in os.getenv(
                "PCR_CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if value.strip()
        )
        if not configured_origins or "*" in configured_origins:
            raise ValueError("PCR_CORS_ORIGINS must be a non-empty explicit allowlist")
        return cls(
            database_url=database_url,
            application_version=os.getenv("PCR_APPLICATION_VERSION", "3.0.0-a5"),
            cors_origins=configured_origins,
        )

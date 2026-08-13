from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _environment_bool(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default

    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be an explicit boolean value")


@dataclass(frozen=True)
class Settings:
    database_url: str
    application_version: str = "3.0.0-b4"
    api_version: str = "v1"
    pve_library_catalog_path: Path | None = None
    pve_library_asset_dir: Path | None = None
    pve_library_external_icons_enabled: bool = False
    gacha_library_catalog_path: Path | None = None
    gacha_library_docx_path: Path | None = None
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )

    def __post_init__(self) -> None:
        catalog_path = self.pve_library_catalog_path
        asset_dir = self.pve_library_asset_dir
        if (catalog_path is None) != (asset_dir is None):
            raise ValueError(
                "PCR_PVE_LIBRARY_CATALOG_PATH and PCR_PVE_LIBRARY_ASSET_DIR "
                "must be configured together"
            )
        if catalog_path is not None:
            object.__setattr__(self, "pve_library_catalog_path", Path(catalog_path))
            object.__setattr__(self, "pve_library_asset_dir", Path(asset_dir))
        if type(self.pve_library_external_icons_enabled) is not bool:
            raise TypeError("pve_library_external_icons_enabled must be a boolean")
        gacha_catalog_path = self.gacha_library_catalog_path
        gacha_docx_path = self.gacha_library_docx_path
        if (gacha_catalog_path is None) != (gacha_docx_path is None):
            raise ValueError(
                "PCR_GACHA_LIBRARY_CATALOG_PATH and PCR_GACHA_LIBRARY_DOCX_PATH "
                "must be configured together"
            )
        if gacha_catalog_path is not None:
            object.__setattr__(
                self,
                "gacha_library_catalog_path",
                Path(gacha_catalog_path),
            )
            object.__setattr__(
                self,
                "gacha_library_docx_path",
                Path(gacha_docx_path),
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
        catalog_value = os.getenv("PCR_PVE_LIBRARY_CATALOG_PATH", "").strip()
        asset_value = os.getenv("PCR_PVE_LIBRARY_ASSET_DIR", "").strip()
        if bool(catalog_value) != bool(asset_value):
            raise ValueError(
                "PCR_PVE_LIBRARY_CATALOG_PATH and PCR_PVE_LIBRARY_ASSET_DIR "
                "must be configured together"
            )
        gacha_catalog_value = os.getenv(
            "PCR_GACHA_LIBRARY_CATALOG_PATH", ""
        ).strip()
        gacha_docx_value = os.getenv("PCR_GACHA_LIBRARY_DOCX_PATH", "").strip()
        if bool(gacha_catalog_value) != bool(gacha_docx_value):
            raise ValueError(
                "PCR_GACHA_LIBRARY_CATALOG_PATH and PCR_GACHA_LIBRARY_DOCX_PATH "
                "must be configured together"
            )
        return cls(
            database_url=database_url,
            application_version=os.getenv("PCR_APPLICATION_VERSION", "3.0.0-b4"),
            pve_library_catalog_path=Path(catalog_value) if catalog_value else None,
            pve_library_asset_dir=Path(asset_value) if asset_value else None,
            pve_library_external_icons_enabled=_environment_bool(
                "PCR_PVE_LIBRARY_EXTERNAL_ICONS_ENABLED"
            ),
            gacha_library_catalog_path=(
                Path(gacha_catalog_value) if gacha_catalog_value else None
            ),
            gacha_library_docx_path=(
                Path(gacha_docx_value) if gacha_docx_value else None
            ),
            cors_origins=configured_origins,
        )

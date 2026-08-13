from __future__ import annotations

import json
import re
from dataclasses import dataclass


ESTERTION_UNIT_ICON_ORIGIN = "https://redive.estertion.win/icon/unit"

_ICON_ID_RE = re.compile(r"^[0-9]{6}$")
_BASE_ID_RE = re.compile(r"^[0-9]{4}$")
_CURRENT_ICON_RE = re.compile(r"(?<![0-9_])([0-9]{6})\.webp(?!_)")
_NAMES_OBJECT_RE = re.compile(
    r"\bnames\s*=\s*(\{.*?\})\s*;\s*Object\.keys",
    re.DOTALL,
)


@dataclass(frozen=True)
class EsterTionIndex:
    """Offline index parsed from a saved EsterTion unit directory page."""

    icon_ids: frozenset[str]
    names_by_icon_id: dict[str, str]

    def bases_for_name(self, jp_name: str | None) -> tuple[str, ...]:
        if not isinstance(jp_name, str) or not jp_name.strip():
            return ()

        exact_name = jp_name.strip()
        bases = {
            icon_id[:4]
            for icon_id, name in self.names_by_icon_id.items()
            if name == exact_name and icon_id in self.icon_ids
        }
        return tuple(sorted(bases))

    def has_base(self, base_id: str) -> bool:
        return bool(_BASE_ID_RE.fullmatch(base_id)) and any(
            icon_id.startswith(base_id) for icon_id in self.icon_ids
        )

    def icon_id(self, base_id: str, rarity: int) -> str | None:
        if not _BASE_ID_RE.fullmatch(base_id) or rarity not in {1, 3, 6}:
            return None
        candidate = f"{base_id}{rarity}1"
        return candidate if candidate in self.icon_ids else None

    def icon_url(self, icon_id: str) -> str | None:
        if not _ICON_ID_RE.fullmatch(icon_id) or icon_id not in self.icon_ids:
            return None
        return f"{ESTERTION_UNIT_ICON_ORIGIN}/{icon_id}.webp"


def parse_estertion_index(snapshot: str) -> EsterTionIndex:
    """Parse IDs and the embedded JP-name map without making network requests."""

    if not isinstance(snapshot, str):
        raise TypeError("snapshot must be text")

    icon_ids = frozenset(_CURRENT_ICON_RE.findall(snapshot))
    names_match = _NAMES_OBJECT_RE.search(snapshot)
    if names_match is None:
        names_by_icon_id: dict[str, str] = {}
    else:
        raw_names = json.loads(names_match.group(1))
        if not isinstance(raw_names, dict):
            raise ValueError("EsterTion names metadata must be a JSON object")
        names_by_icon_id = {
            icon_id: name.strip()
            for icon_id, name in raw_names.items()
            if isinstance(icon_id, str)
            and _ICON_ID_RE.fullmatch(icon_id)
            and isinstance(name, str)
            and name.strip()
        }

    return EsterTionIndex(
        icon_ids=icon_ids,
        names_by_icon_id=names_by_icon_id,
    )

from __future__ import annotations

import re
from typing import Any

from .models import SourceRef


SOURCE_ALIASES = {
    "#1": ("クランバトル情報会 Discord", "UNLOCATED"),
    "#2": ("WorryChefs 深域整合表格", "UNLOCATED"),
    "#3": ("GameWith", "NAMED_NO_LOCATOR"),
    "#4": ("帝国華撃団 Wiki", "NAMED_NO_LOCATOR"),
}
_SOURCE_TOKEN = re.compile(r"https?://[^\s\"<>]+|(?<!\w)#[1-4](?!\d)")
_HYPERLINK_FORMULA = re.compile(
    r'^\s*=\s*HYPERLINK\s*\(\s*"((?:[^"]|"")*)"',
    re.IGNORECASE,
)
_TRAILING_URL_PUNCTUATION = ".,;，。；)]}）】"


def _hyperlink_value(cell: Any) -> str | None:
    hyperlink = getattr(cell, "hyperlink", None)
    if hyperlink is None:
        return None
    return (getattr(hyperlink, "target", None) or getattr(hyperlink, "location", None))


def extract_source_refs(
    cell: Any,
    *,
    sheet_name: str,
    applies_to_cell: str | None = None,
) -> tuple[SourceRef, ...]:
    """Extract URLs and workbook aliases without cross-row inheritance."""

    origin = f"{sheet_name}!{cell.coordinate}"
    raw = "" if cell.value is None else str(cell.value)
    refs: list[SourceRef] = []
    seen: set[tuple[str, str]] = set()

    formula_match = _HYPERLINK_FORMULA.match(raw)
    scan_text = raw
    if formula_match is not None:
        formula_target = formula_match.group(1).replace('""', '"')
        if formula_target.startswith(("http://", "https://")):
            refs.append(
                SourceRef(
                    kind="URL",
                    label_raw=raw,
                    origin_cell=origin,
                    url=formula_target,
                    applies_to_cell=applies_to_cell,
                )
            )
            seen.add(("URL", formula_target))
        elif formula_target.startswith("#"):
            refs.append(
                SourceRef(
                    kind="INTERNAL_SHEET",
                    label_raw=raw,
                    origin_cell=origin,
                    url=formula_target,
                    resolution_status="INTERNAL",
                    applies_to_cell=applies_to_cell,
                )
            )
            seen.add(("INTERNAL_SHEET", formula_target))
        else:
            refs.append(
                SourceRef(
                    kind="UNRESOLVED_FORMULA",
                    label_raw=raw,
                    origin_cell=origin,
                    resolution_status="UNSUPPORTED_TARGET",
                    applies_to_cell=applies_to_cell,
                )
            )
        # Do not let the generic URL matcher consume the formula's label and
        # closing syntax as part of the URL.
        scan_text = ""
    elif raw.lstrip().upper().startswith("=HYPERLINK"):
        refs.append(
            SourceRef(
                kind="UNRESOLVED_FORMULA",
                label_raw=raw,
                origin_cell=origin,
                resolution_status="UNPARSEABLE_FORMULA",
                applies_to_cell=applies_to_cell,
            )
        )
        scan_text = ""

    for match in _SOURCE_TOKEN.finditer(scan_text):
        token = match.group(0)
        if token.startswith(("http://", "https://")):
            url = token.rstrip(_TRAILING_URL_PUNCTUATION)
            key = ("URL", url)
            if key not in seen:
                refs.append(
                    SourceRef(
                        kind="URL",
                        label_raw=token,
                        origin_cell=origin,
                        url=url,
                        applies_to_cell=applies_to_cell,
                    )
                )
                seen.add(key)
            continue
        alias_label, status = SOURCE_ALIASES[token]
        key = ("WORKBOOK_ALIAS", token)
        if key not in seen:
            refs.append(
                SourceRef(
                    kind="WORKBOOK_ALIAS",
                    label_raw=token,
                    origin_cell=origin,
                    alias_id=token,
                    alias_label=alias_label,
                    resolution_status=status,
                    applies_to_cell=applies_to_cell,
                )
            )
            seen.add(key)

    hyperlink = _hyperlink_value(cell)
    if hyperlink:
        if hyperlink.startswith(("http://", "https://")):
            key = ("URL", hyperlink)
            if key not in seen:
                refs.append(
                    SourceRef(
                        kind="URL",
                        label_raw=raw or hyperlink,
                        origin_cell=origin,
                        url=hyperlink,
                        applies_to_cell=applies_to_cell,
                    )
                )
        else:
            key = ("INTERNAL_SHEET", hyperlink)
            if key not in seen:
                refs.append(
                    SourceRef(
                        kind="INTERNAL_SHEET",
                        label_raw=raw or hyperlink,
                        origin_cell=origin,
                        url=hyperlink,
                        resolution_status="INTERNAL",
                        applies_to_cell=applies_to_cell,
                    )
                )
    return tuple(refs)

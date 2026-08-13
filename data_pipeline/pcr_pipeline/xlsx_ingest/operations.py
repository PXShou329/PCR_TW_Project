from __future__ import annotations

import re
import unicodedata

from .models import OperationVariant, ParsedOperation


_SET_TOKEN = re.compile(r"全\s*SET|(?<![A-Z])[OX]{5}(?![A-Z])", re.IGNORECASE)


def _operation_kind(variants: list[OperationVariant], hints: list[str]) -> str:
    categories = (["SET_CONFIGURATION"] if variants else []) + hints
    if not categories:
        return "UNKNOWN"
    if len(set(categories)) == 1:
        return categories[0]
    return "COMPOSITE"


def parse_operation(
    raw: str,
    *,
    origin_field: str = "OPERATION_TEXT",
    origin_cell: str | None = None,
) -> ParsedOperation:
    """Preserve source text while normalizing only explicit SET state tokens.

    O means SET and X means not SET.  The five positions follow the workbook's
    left-to-right portrait order.  A positional pattern is not an AUTO mode and
    is never expanded into five invented timeline steps.
    """

    normalized = unicodedata.normalize("NFKC", raw)
    variants: list[OperationVariant] = []
    for match in _SET_TOKEN.finditer(normalized):
        token = match.group(0).replace(" ", "")
        if token.upper() == "全SET":
            variants.append(
                OperationVariant(
                    kind="FULL_SET",
                    raw=match.group(0),
                    source_order_states=("SET",) * 5,
                    origin_field=origin_field,
                    origin_cell=origin_cell,
                )
            )
            continue
        pattern = token.upper()
        variants.append(
            OperationVariant(
                kind="POSITIONAL_PATTERN",
                raw=match.group(0),
                source_order_states=tuple(
                    "SET" if marker == "O" else "NOT_SET" for marker in pattern
                ),
                origin_field=origin_field,
                origin_cell=origin_cell,
            )
        )

    hints: list[str] = []
    if "半自動" in normalized or re.search(r"半\s*A", normalized, re.IGNORECASE):
        hints.append("SEMI_AUTO")
    if re.search(r"目[押壓]", normalized):
        hints.append("MANUAL_CUE")
    if "手動" in normalized:
        hints.append("MANUAL")

    return ParsedOperation(
        kind=_operation_kind(variants, hints),
        order_basis="WORKBOOK_TEXT_LEFT_TO_RIGHT",
        member_alignment="UNRESOLVED",
        variants=tuple(variants),
        execution_hints=tuple(hints),
    )


def merge_parsed_operations(*operations: ParsedOperation) -> ParsedOperation:
    """Combine explicit tokens from separate workbook fields without losing origin."""

    variants = [variant for operation in operations for variant in operation.variants]
    hints: list[str] = []
    for operation in operations:
        for hint in operation.execution_hints:
            if hint not in hints:
                hints.append(hint)
    return ParsedOperation(
        kind=_operation_kind(variants, hints),
        order_basis="WORKBOOK_TEXT_LEFT_TO_RIGHT",
        member_alignment="UNRESOLVED",
        variants=tuple(variants),
        execution_hints=tuple(hints),
    )

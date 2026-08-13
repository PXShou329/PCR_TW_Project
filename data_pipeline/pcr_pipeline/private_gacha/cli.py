from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from .docx import GachaDocxError, canonical_json_bytes, extract_gacha_forecast_docx


def write_atomic(path: str | Path, payload: bytes) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract a user-supplied Gacha forecast DOCX into candidate JSON"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    input_path = args.input.resolve(strict=False)
    output_path = args.output.resolve(strict=False)
    if input_path == output_path:
        parser.error("--output must not overwrite the source DOCX")
    if input_path.suffix.lower() != ".docx":
        parser.error("--input must use a .docx filename")
    if output_path.suffix.lower() != ".json":
        parser.error("--output must use a .json filename")

    try:
        bundle = extract_gacha_forecast_docx(
            input_path,
            source_id=args.source_id,
        )
    except GachaDocxError as exc:
        parser.error(str(exc))
    write_atomic(output_path, canonical_json_bytes(bundle))
    print(json.dumps(bundle["summary"], ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

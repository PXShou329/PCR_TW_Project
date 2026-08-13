from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .catalog import export_staging_media, merge_staging_catalog_files
from .character_mapping import map_catalog_characters
from .deep_1_7 import extract_deep_1_7_workbook
from .estertion_index import parse_estertion_index
from .portrait_review import (
    build_materialization_manifest,
    build_portrait_review_queue,
    canonical_json_bytes,
    formation_asset_sha256s,
    load_strict_json,
    materialize_character_catalog,
    validate_override_registry,
    verify_evidence_files,
)
from .workbook_2 import extract_workbook_2


def format_stdout_summary(summary: object) -> str:
    """Serialize the status line so it is safe on legacy Windows consoles."""

    return json.dumps(summary, ensure_ascii=True, sort_keys=True)


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
        description="Extract private PvE XLSX data into deterministic staging JSON"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    extract = subparsers.add_parser("extract")
    workbook_2 = subparsers.add_parser("extract-workbook-2")
    for command in (extract, workbook_2):
        command.add_argument("--input", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument(
            "--allow-partial-layout",
            action="store_true",
            help="Development fixtures only; production extraction is strict by default.",
        )
    export_media = subparsers.add_parser(
        "export-media",
        help="Verify a workbook/staging pair and export exact embedded bytes.",
    )
    export_media.add_argument("--input", type=Path, required=True)
    export_media.add_argument("--catalog", type=Path, required=True)
    export_media.add_argument("--output-dir", type=Path, required=True)
    merge_catalogs = subparsers.add_parser(
        "merge-catalogs",
        help="Merge two or more private PvE staging JSON catalogs.",
    )
    merge_catalogs.add_argument(
        "--input",
        action="append",
        type=Path,
        required=True,
        help="Repeat once for each staging .json file.",
    )
    merge_catalogs.add_argument("--output", type=Path, required=True)
    review_queue = subparsers.add_parser(
        "build-review-queue",
        help="Build a deterministic queue of formation portrait identities.",
    )
    review_queue.add_argument("--catalog", type=Path, required=True)
    review_queue.add_argument("--overrides", type=Path)
    review_queue.add_argument("--output", type=Path, required=True)
    materialize = subparsers.add_parser(
        "materialize-character-catalog",
        help="Apply reviewed exact-unit mappings to a derived local catalog.",
    )
    materialize.add_argument("--catalog", type=Path, required=True)
    materialize.add_argument("--overrides", type=Path, required=True)
    materialize.add_argument("--estertion-index", type=Path, required=True)
    materialize.add_argument("--evidence-dir", type=Path, required=True)
    materialize.add_argument("--output", type=Path, required=True)
    materialize.add_argument("--mapping-output", type=Path, required=True)
    materialize.add_argument("--manifest-output", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.command in {"extract", "extract-workbook-2"}:
        input_path = args.input.resolve(strict=False)
        output_path = args.output.resolve(strict=False)
        if input_path == output_path:
            parser.error("--output must not overwrite the source workbook")
        if output_path.suffix.lower() != ".json":
            parser.error("--output must use a .json filename")

        extractor = (
            extract_deep_1_7_workbook
            if args.command == "extract"
            else extract_workbook_2
        )
        result = extractor(
            input_path,
            strict=not args.allow_partial_layout,
        )
        write_atomic(output_path, result.canonical_json_bytes())
        summary = result.summary
    elif args.command == "export-media":
        if args.catalog.suffix.lower() != ".json":
            parser.error("--catalog must use a .json filename")
        summary = export_staging_media(
            workbook_path=args.input,
            staging_catalog_path=args.catalog,
            output_directory=args.output_dir,
        )
    elif args.command == "merge-catalogs":
        input_paths = [path.resolve(strict=False) for path in args.input]
        output_path = args.output.resolve(strict=False)
        if len(input_paths) < 2:
            parser.error("merge-catalogs requires at least two --input files")
        if len(set(input_paths)) != len(input_paths):
            parser.error("merge-catalogs --input paths must be distinct")
        if any(path.suffix.lower() != ".json" for path in input_paths):
            parser.error("every merge-catalogs --input must use a .json filename")
        if output_path.suffix.lower() != ".json":
            parser.error("--output must use a .json filename")
        if output_path in set(input_paths):
            parser.error("--output must not overwrite a staging input")
        result = merge_staging_catalog_files(input_paths)
        write_atomic(output_path, result.canonical_json_bytes())
        summary = result.summary
    elif args.command == "build-review-queue":
        catalog_path = args.catalog.resolve(strict=False)
        output_path = args.output.resolve(strict=False)
        override_path = (
            args.overrides.resolve(strict=False)
            if args.overrides is not None
            else None
        )
        _require_json_path(parser, catalog_path, "--catalog")
        _require_json_path(parser, output_path, "--output")
        if override_path is not None:
            _require_json_path(parser, override_path, "--overrides")
        input_paths = {catalog_path}
        if override_path is not None:
            input_paths.add(override_path)
        if output_path in input_paths:
            parser.error("--output must not overwrite a review input")

        catalog = load_strict_json(catalog_path)
        if override_path is None:
            overrides = None
            override_sha256 = None
        else:
            loaded_overrides = load_strict_json(override_path)
            overrides = loaded_overrides.document
            override_sha256 = loaded_overrides.sha256
        queue = build_portrait_review_queue(
            catalog.document,
            catalog_sha256=catalog.sha256,
            overrides=overrides,
            override_registry_sha256=override_sha256,
        )
        write_atomic(output_path, canonical_json_bytes(queue))
        summary = queue["summary"]
    else:
        catalog_path = args.catalog.resolve(strict=False)
        override_path = args.overrides.resolve(strict=False)
        estertion_path = args.estertion_index.resolve(strict=False)
        evidence_directory = args.evidence_dir.resolve(strict=False)
        output_path = args.output.resolve(strict=False)
        mapping_path = args.mapping_output.resolve(strict=False)
        manifest_path = args.manifest_output.resolve(strict=False)
        for path, flag in (
            (catalog_path, "--catalog"),
            (override_path, "--overrides"),
            (output_path, "--output"),
            (mapping_path, "--mapping-output"),
            (manifest_path, "--manifest-output"),
        ):
            _require_json_path(parser, path, flag)
        input_paths = {catalog_path, override_path, estertion_path}
        output_paths = {output_path, mapping_path, manifest_path}
        if len(output_paths) != 3:
            parser.error("materialization output paths must be distinct")
        if input_paths & output_paths:
            parser.error("materialization outputs must not overwrite inputs")
        if not estertion_path.is_file():
            parser.error("--estertion-index must be an existing snapshot file")

        catalog = load_strict_json(catalog_path)
        loaded_overrides = load_strict_json(override_path)
        formation_shas = formation_asset_sha256s(catalog.document)
        overrides = validate_override_registry(
            loaded_overrides.document,
            formation_sha256s=formation_shas,
            base_catalog_sha256=catalog.sha256,
        )
        evidence_source_paths = {
            (evidence_directory / item["filename"]).resolve(strict=False)
            for item in overrides["evidence"].values()
        }
        if output_paths & evidence_source_paths:
            parser.error("materialization outputs must not overwrite evidence inputs")
        verified_evidence = verify_evidence_files(overrides, evidence_directory)
        try:
            estertion_bytes = estertion_path.read_bytes()
            estertion_snapshot = estertion_bytes.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            parser.error(f"cannot read --estertion-index as UTF-8: {type(exc).__name__}")
        estertion_sha256 = hashlib.sha256(estertion_bytes).hexdigest()
        mapping = map_catalog_characters(
            catalog.document,
            overrides,
            parse_estertion_index(estertion_snapshot),
            asset_sha256s=formation_shas,
        )
        mapped_catalog = materialize_character_catalog(catalog.document, mapping)
        manifest = build_materialization_manifest(
            base_catalog_sha256=catalog.sha256,
            override_registry_sha256=loaded_overrides.sha256,
            estertion_index_sha256=estertion_sha256,
            overrides=overrides,
            verified_evidence_sha256s=verified_evidence,
            mapping_manifest=mapping,
            mapped_catalog=mapped_catalog,
        )
        # Every input is validated and every payload is built before any output is
        # touched.  Each individual artifact is then written via same-directory
        # fsync + atomic replace.
        write_atomic(mapping_path, canonical_json_bytes(mapping))
        write_atomic(output_path, canonical_json_bytes(mapped_catalog))
        write_atomic(manifest_path, canonical_json_bytes(manifest))
        summary = mapping["summary"]

    # Keep command-line output encodable on Windows consoles that still use a
    # legacy code page (for example cp950).  JSON artifacts themselves remain
    # canonical UTF-8; only this one-line status payload is escaped for stdout.
    print(format_stdout_summary(summary))
    return 0


def _require_json_path(
    parser: argparse.ArgumentParser,
    path: Path,
    flag: str,
) -> None:
    if path.suffix.lower() != ".json":
        parser.error(f"{flag} must use a .json filename")


if __name__ == "__main__":
    raise SystemExit(main())

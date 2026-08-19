"""Validate tracked provenance metadata against an ignored local snapshot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_PROVENANCE_PATH = Path("data/raw/provenance.json")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ProvenanceMetadataError(ValueError):
    """Raised when tracked provenance metadata cannot be validated safely."""


@dataclass(frozen=True)
class ProvenanceValidationResult:
    """The result of comparing metadata with a local raw snapshot."""

    passed: bool
    snapshot_available: bool
    provenance_path: Path
    snapshot_path: Path
    errors: tuple[str, ...] = ()


def validate_provenance(
    provenance_path: Path = DEFAULT_PROVENANCE_PATH,
    *,
    raw_path: Path | None = None,
    project_root: Path | None = None,
) -> ProvenanceValidationResult:
    """Compare tracked metadata with a local raw CSV snapshot.

    The raw snapshot is intentionally not downloaded by this function.  A
    missing snapshot returns a failed result with ``snapshot_available=False``
    so callers can distinguish unavailable evidence from a mismatch.  The
    command-line entry point may explicitly turn that one state into a skipped
    CI check with ``--allow-missing``; mismatches never become passes.
    """
    provenance_path = Path(provenance_path).resolve()
    metadata = _read_metadata(provenance_path)
    snapshot_metadata = _snapshot_metadata(metadata)
    root = _project_root(provenance_path, project_root)
    snapshot_path = _resolve_snapshot_path(
        snapshot_metadata["path"],
        root,
        raw_path,
    )
    expected_hash = snapshot_metadata["sha256"]
    expected_size = snapshot_metadata["size_bytes"]
    expected_columns = snapshot_metadata["source_columns"]
    expected_row_count = snapshot_metadata.get("row_count")

    if not snapshot_path.exists():
        return ProvenanceValidationResult(
            passed=False,
            snapshot_available=False,
            provenance_path=provenance_path,
            snapshot_path=snapshot_path,
            errors=(f"raw snapshot unavailable: {snapshot_path}",),
        )

    if not snapshot_path.is_file():
        return ProvenanceValidationResult(
            passed=False,
            snapshot_available=True,
            provenance_path=provenance_path,
            snapshot_path=snapshot_path,
            errors=(f"raw snapshot is not a regular file: {snapshot_path}",),
        )

    errors: list[str] = []
    try:
        actual_hash = _sha256(snapshot_path)
        actual_size = snapshot_path.stat().st_size
    except OSError as exc:
        return ProvenanceValidationResult(
            passed=False,
            snapshot_available=True,
            provenance_path=provenance_path,
            snapshot_path=snapshot_path,
            errors=(f"could not read raw snapshot: {exc}",),
        )

    if actual_hash != expected_hash:
        errors.append("sha256 mismatch between tracked metadata and raw snapshot")
    if actual_size != expected_size:
        errors.append(
            f"size_bytes mismatch (tracked {expected_size}, local {actual_size})"
        )

    try:
        actual_columns, actual_row_count = _csv_measurements(snapshot_path)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        errors.append(f"could not inspect CSV schema: {exc}")
    else:
        if actual_columns != expected_columns:
            errors.append("source_columns schema mismatch between metadata and raw snapshot")
        if expected_row_count is not None and actual_row_count != expected_row_count:
            errors.append(
                f"row_count mismatch (tracked {expected_row_count}, local {actual_row_count})"
            )

    return ProvenanceValidationResult(
        passed=not errors,
        snapshot_available=True,
        provenance_path=provenance_path,
        snapshot_path=snapshot_path,
        errors=tuple(errors),
    )


def _read_metadata(path: Path) -> Mapping[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProvenanceMetadataError(f"cannot read provenance metadata: {exc}") from exc

    try:
        metadata = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProvenanceMetadataError(f"provenance metadata is not valid JSON: {exc}") from exc

    if not isinstance(metadata, Mapping):
        raise ProvenanceMetadataError("provenance metadata must contain a JSON object")
    return metadata


def _snapshot_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = metadata.get("local_snapshot")
    if not isinstance(snapshot, Mapping):
        raise ProvenanceMetadataError("provenance metadata lacks a local_snapshot object")

    path = _required_string(snapshot, "path")
    digest = _required_string(snapshot, "sha256").lower()
    if not _SHA256.fullmatch(digest):
        raise ProvenanceMetadataError("local_snapshot.sha256 must be a 64-character hex digest")

    size_bytes = _required_nonnegative_int(snapshot, "size_bytes")
    source_columns = snapshot.get("source_columns")
    if (
        not isinstance(source_columns, list)
        or not source_columns
        or not all(isinstance(column, str) for column in source_columns)
    ):
        raise ProvenanceMetadataError(
            "local_snapshot.source_columns must be a non-empty list of strings"
        )

    normalized: dict[str, Any] = {
        "path": path,
        "sha256": digest,
        "size_bytes": size_bytes,
        "source_columns": source_columns,
    }
    if "row_count" in snapshot:
        normalized["row_count"] = _required_nonnegative_int(snapshot, "row_count")
    return normalized


def _required_string(values: Mapping[str, Any], name: str) -> str:
    value = values.get(name)
    if not isinstance(value, str) or not value:
        raise ProvenanceMetadataError(f"local_snapshot.{name} must be a non-empty string")
    return value


def _required_nonnegative_int(values: Mapping[str, Any], name: str) -> int:
    value = values.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProvenanceMetadataError(f"local_snapshot.{name} must be a non-negative integer")
    return value


def _project_root(provenance_path: Path, project_root: Path | None) -> Path:
    if project_root is not None:
        return Path(project_root).resolve()

    # The repository layout is data/raw/provenance.json.  Falling back to the
    # metadata directory keeps temporary metadata fixtures convenient to use.
    if provenance_path.parent.name == "raw" and provenance_path.parent.parent.name == "data":
        return provenance_path.parent.parent.parent
    return provenance_path.parent


def _resolve_snapshot_path(
    metadata_path: str,
    project_root: Path,
    raw_path: Path | None,
) -> Path:
    if raw_path is not None:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = project_root / candidate
        return candidate.resolve()

    candidate = Path(metadata_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (project_root / candidate).resolve()

    try:
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise ProvenanceMetadataError(
            "local_snapshot.path must stay within the project root"
        ) from exc
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_measurements(path: Path) -> tuple[list[str], int]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, strict=True)
        try:
            columns = next(reader)
        except StopIteration as exc:
            raise ValueError("CSV has no header row") from exc
        row_count = sum(1 for row in reader if row)
    return columns, row_count


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare tracked provenance metadata with the ignored local raw CSV. "
            "No data is downloaded."
        )
    )
    parser.add_argument(
        "--provenance",
        type=Path,
        default=DEFAULT_PROVENANCE_PATH,
        help="tracked provenance JSON path (default: data/raw/provenance.json)",
    )
    parser.add_argument(
        "--raw",
        dest="raw_path",
        type=Path,
        help="optional local raw CSV path override",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="root used to resolve a repository-relative snapshot path",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help=(
            "treat an unavailable ignored snapshot as an explicit skip; metadata "
            "errors and mismatches still fail"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the provenance validator and return a process exit code."""
    args = _parser().parse_args(argv)
    try:
        result = validate_provenance(
            args.provenance,
            raw_path=args.raw_path,
            project_root=args.project_root,
        )
    except ProvenanceMetadataError as exc:
        print(f"ERROR: invalid provenance metadata: {exc}", file=sys.stderr)
        return 1

    if result.passed:
        print(
            "PASS: tracked provenance matches the local raw snapshot "
            f"({result.snapshot_path})."
        )
        return 0

    if not result.snapshot_available:
        message = result.errors[0]
        if args.allow_missing:
            print(
                f"SKIP: {message}; no local snapshot validation was performed. "
                "This is unavailable evidence, not a measured match."
            )
            return 0
        print(f"ERROR: {message}", file=sys.stderr)
        print(
            "Download the pinned public snapshot with `python scripts/download_data.py` "
            "before validating it locally.",
            file=sys.stderr,
        )
        return 1

    print("ERROR: provenance validation failed:", file=sys.stderr)
    for error in result.errors:
        print(f"- {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

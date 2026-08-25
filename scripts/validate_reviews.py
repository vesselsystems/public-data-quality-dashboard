#!/usr/bin/env python3
"""Validate the tracked human-review decisions and report unresolved items."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Sequence

DEFAULT_REVIEWS_PATH = Path(__file__).resolve().parents[1] / "data" / "reviews" / "decisions.json"
REQUIRED_RECORD_KEYS = {
    "id",
    "question",
    "required",
    "evidence_fields",
    "status",
    "decision",
    "reviewer",
    "reviewed_at_utc",
    "rationale",
    "evidence_refs",
}
VALID_STATUSES = {"pending", "approved", "rejected"}
TERMINAL_STATUSES = {"approved", "rejected"}
EXPECTED_REVIEW_IDS = frozenset(
    {
        "dataset_terms_legal_review",
        "screenshot_decision",
        "deployment_authorization",
    }
)


@dataclass(frozen=True)
class ValidationResult:
    """Validation errors and the review counts derived from valid records."""

    errors: tuple[str, ...]
    pending_ids: tuple[str, ...]
    completed_ids: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _blank(value: Any) -> bool:
    return value is None or value == ""


def _valid_utc_timestamp(value: Any) -> bool:
    if not _nonempty_text(value):
        return False
    timestamp = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0)


def _validate_record(
    record: dict[str, Any], index: int, seen_ids: set[str]
) -> tuple[list[str], str | None]:
    errors: list[str] = []
    label = f"reviews[{index}]"
    missing = sorted(REQUIRED_RECORD_KEYS - record.keys())
    if missing:
        errors.append(f"{label} missing required keys: {', '.join(missing)}")

    record_id = record.get("id")
    if not _nonempty_text(record_id):
        errors.append(f"{label}.id must be a non-empty string")
        record_id = None
    elif record_id in seen_ids:
        errors.append(f"duplicate review id: {record_id}")
    else:
        seen_ids.add(record_id)

    if not _nonempty_text(record.get("question")):
        errors.append(f"{label}.question must be a non-empty string")
    if not isinstance(record.get("required"), bool):
        errors.append(f"{label}.required must be a boolean")

    evidence_fields = record.get("evidence_fields")
    if not isinstance(evidence_fields, list) or not evidence_fields:
        errors.append(f"{label}.evidence_fields must be a non-empty list")
        evidence_fields = []
    valid_evidence_fields = [field for field in evidence_fields if _nonempty_text(field)]
    if len(valid_evidence_fields) != len(evidence_fields):
        errors.append(f"{label}.evidence_fields must contain non-empty strings")
    if len(valid_evidence_fields) != len(set(valid_evidence_fields)):
        errors.append(f"{label}.evidence_fields must not contain duplicates")

    evidence_refs = record.get("evidence_refs")
    if not isinstance(evidence_refs, dict):
        errors.append(f"{label}.evidence_refs must be an object")
        evidence_refs = {}
    else:
        unknown_refs = sorted(set(evidence_refs) - set(valid_evidence_fields))
        if unknown_refs:
            errors.append(
                f"{label}.evidence_refs has fields not listed in evidence_fields: "
                + ", ".join(unknown_refs)
            )
        for field, reference in evidence_refs.items():
            if not _nonempty_text(reference):
                errors.append(f"{label}.evidence_refs.{field} must be a non-empty string")

    status = record.get("status")
    if not isinstance(status, str) or status not in VALID_STATUSES:
        errors.append(
            f"{label}.status must be exactly one of: "
            + ", ".join(sorted(VALID_STATUSES))
        )
        return errors, record_id

    if status == "pending":
        for field in ("decision", "reviewer", "reviewed_at_utc", "rationale"):
            if not _blank(record.get(field)):
                errors.append(f"{label}.{field} must be null or empty while pending")
    else:
        for field in ("decision", "reviewer", "rationale"):
            if not _nonempty_text(record.get(field)):
                errors.append(f"{label}.{field} is required for {status} records")
        if not _valid_utc_timestamp(record.get("reviewed_at_utc")):
            errors.append(f"{label}.reviewed_at_utc must be a valid UTC timestamp")
        missing_evidence = [
            field
            for field in valid_evidence_fields
            if field not in evidence_refs or not _nonempty_text(evidence_refs[field])
        ]
        if missing_evidence:
            errors.append(
                f"{label} {status} decision is missing evidence: " + ", ".join(missing_evidence)
            )

    return errors, record_id


def validate_reviews(path: Path) -> ValidationResult:
    """Validate a review file without treating pending records as complete."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return ValidationResult((f"cannot read {path}: {exc}",), (), ())
    except json.JSONDecodeError as exc:
        return ValidationResult((f"malformed JSON in {path}: {exc}",), (), ())

    errors: list[str] = []
    if not isinstance(payload, dict):
        return ValidationResult(("top-level JSON value must be an object",), (), ())
    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    records = payload.get("reviews")
    if not isinstance(records, list):
        errors.append("reviews must be a list")
        return ValidationResult(tuple(errors), (), ())

    seen_ids: set[str] = set()
    pending_ids: list[str] = []
    completed_ids: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"reviews[{index}] must be an object")
            continue
        record_errors, record_id = _validate_record(record, index, seen_ids)
        errors.extend(record_errors)
        status = record.get("status")
        if record_id is not None and status == "pending":
            pending_ids.append(record_id)
        elif record_id is not None and isinstance(status, str) and status in TERMINAL_STATUSES:
            completed_ids.append(record_id)

    missing_ids = sorted(EXPECTED_REVIEW_IDS - seen_ids)
    extra_ids = sorted(seen_ids - EXPECTED_REVIEW_IDS)
    if missing_ids:
        errors.append("missing expected review IDs: " + ", ".join(missing_ids))
    if extra_ids:
        errors.append("unexpected review IDs: " + ", ".join(extra_ids))

    return ValidationResult(tuple(errors), tuple(pending_ids), tuple(completed_ids))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reviews",
        type=Path,
        default=DEFAULT_REVIEWS_PATH,
        help="path to the review decisions JSON file",
    )
    args = parser.parse_args(argv)
    result = validate_reviews(args.reviews)

    if not result.passed:
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        f"Validated {len(result.completed_ids) + len(result.pending_ids)} review items: "
        f"{len(result.completed_ids)} complete, {len(result.pending_ids)} pending."
    )
    if result.pending_ids:
        print("Pending: " + ", ".join(result.pending_ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

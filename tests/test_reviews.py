import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
VALIDATOR = ROOT / "scripts" / "validate_reviews.py"
TEMPLATE = ROOT / "data" / "reviews" / "decisions.json"


def run_validator(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--reviews", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_tracked_template_is_valid_and_pending_items_are_not_complete() -> None:
    result = run_validator(TEMPLATE)

    assert result.returncode == 0
    assert "0 complete, 3 pending" in result.stdout
    assert "dataset_terms_legal_review" in result.stdout
    assert "screenshot_decision" in result.stdout
    assert "deployment_authorization" in result.stdout


def test_validator_rejects_malformed_json(tmp_path: Path) -> None:
    decisions = tmp_path / "decisions.json"
    decisions.write_text("{not JSON", encoding="utf-8")

    result = run_validator(decisions)

    assert result.returncode == 1
    assert "malformed JSON" in result.stderr


def test_validator_rejects_missing_expected_record(tmp_path: Path) -> None:
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    payload["reviews"] = payload["reviews"][:2]
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps(payload), encoding="utf-8")

    result = run_validator(decisions)

    assert result.returncode == 1
    assert "missing expected review IDs: deployment_authorization" in result.stderr


def test_validator_rejects_extra_record(tmp_path: Path) -> None:
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    extra_review = dict(payload["reviews"][0])
    extra_review["id"] = "unexpected_review"
    payload["reviews"].append(extra_review)
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps(payload), encoding="utf-8")

    result = run_validator(decisions)

    assert result.returncode == 1
    assert "unexpected review IDs: unexpected_review" in result.stderr


def test_validator_rejects_duplicate_ids_and_unknown_status(tmp_path: Path) -> None:
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    payload["reviews"][1]["id"] = payload["reviews"][0]["id"]
    payload["reviews"][2]["status"] = "deferred"
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps(payload), encoding="utf-8")

    result = run_validator(decisions)

    assert result.returncode == 1
    assert "duplicate review id" in result.stderr
    assert "status must be exactly" in result.stderr


def test_validator_rejects_missing_required_record_keys(tmp_path: Path) -> None:
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    payload["reviews"][0].pop("rationale")
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps(payload), encoding="utf-8")

    result = run_validator(decisions)

    assert result.returncode == 1
    assert "missing required keys: rationale" in result.stderr


def test_validator_requires_complete_terminal_evidence_and_utc_time(tmp_path: Path) -> None:
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    review = payload["reviews"][0]
    review.update(
        {
            "status": "approved",
            "decision": "approved",
            "reviewer": "test-reviewer",
            "reviewed_at_utc": "2025-01-01T00:00:00",
            "rationale": "test rationale",
            "evidence_refs": {},
        }
    )
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps(payload), encoding="utf-8")

    result = run_validator(decisions)

    assert result.returncode == 1
    assert "valid UTC timestamp" in result.stderr
    assert "missing evidence" in result.stderr

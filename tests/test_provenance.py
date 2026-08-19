import hashlib
import json
from pathlib import Path

from data_quality_dashboard.provenance import main, validate_provenance

COLUMNS = ["Date", "Max_TemperatureC", "Mean_TemperatureC", "Min_TemperatureC"]


def _write_metadata(tmp_path: Path, raw_name: str = "snapshot.csv") -> Path:
    raw = tmp_path / raw_name
    raw.write_text(
        ",".join(COLUMNS) + "\n2024-01-01,10,7,4\n2024-01-02,12,8,5\n",
        encoding="utf-8",
    )
    metadata = {
        "local_snapshot": {
            "path": raw.name,
            "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            "size_bytes": raw.stat().st_size,
            "source_columns": COLUMNS,
            "row_count": 2,
        }
    }
    provenance = tmp_path / "provenance.json"
    provenance.write_text(json.dumps(metadata), encoding="utf-8")
    return provenance


def test_provenance_matches_local_snapshot(tmp_path: Path) -> None:
    provenance = _write_metadata(tmp_path)

    result = validate_provenance(provenance, project_root=tmp_path)

    assert result.passed is True
    assert result.snapshot_available is True
    assert result.errors == ()


def test_provenance_detects_hash_and_size_mismatch(tmp_path: Path) -> None:
    provenance = _write_metadata(tmp_path)
    (tmp_path / "snapshot.csv").write_text(
        ",".join(COLUMNS) + "\n2024-01-01,10,7,4\n2024-01-02,12,8,500\n",
        encoding="utf-8",
    )

    result = validate_provenance(provenance, project_root=tmp_path)

    assert result.passed is False
    assert result.snapshot_available is True
    assert any("sha256 mismatch" in error for error in result.errors)
    assert any("size_bytes mismatch" in error for error in result.errors)


def test_provenance_detects_schema_mismatch(tmp_path: Path) -> None:
    provenance = _write_metadata(tmp_path)
    metadata = json.loads(provenance.read_text(encoding="utf-8"))
    metadata["local_snapshot"]["source_columns"][-1] = "Unexpected"
    provenance.write_text(json.dumps(metadata), encoding="utf-8")

    result = validate_provenance(provenance, project_root=tmp_path)

    assert result.passed is False
    assert any("schema mismatch" in error for error in result.errors)


def test_provenance_reports_missing_snapshot_without_fabricating_evidence(
    tmp_path: Path,
) -> None:
    provenance = _write_metadata(tmp_path, raw_name="missing.csv")
    (tmp_path / "missing.csv").unlink()

    result = validate_provenance(provenance, project_root=tmp_path)

    assert result.passed is False
    assert result.snapshot_available is False
    assert "unavailable" in result.errors[0]


def test_cli_requires_missing_snapshot_unless_explicitly_allowed(
    tmp_path: Path, capsys
) -> None:
    provenance = _write_metadata(tmp_path, raw_name="missing.csv")
    (tmp_path / "missing.csv").unlink()

    failed = main(["--provenance", str(provenance)])
    failure_output = capsys.readouterr()
    skipped = main(["--provenance", str(provenance), "--allow-missing"])
    skip_output = capsys.readouterr()

    assert failed == 1
    assert "unavailable" in failure_output.err
    assert skipped == 0
    assert "no local snapshot validation" in skip_output.out

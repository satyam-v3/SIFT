"""Regression tests for real-release source and split governance."""

from data_pipeline.release_gate import ReleaseGateAuditor
from data_pipeline.sources import SourceRegistry, RegisteredSource, SourceType, DataClassification, PermissionStatus
from tests.data.test_dataset_release_gates import _high_record


def _registry(tmp_path, source):
    path = tmp_path / "registry.json"
    SourceRegistry(str(path)).register_source(source)
    return str(path)


def test_synthetic_source_cannot_pass_real_release(tmp_path):
    path = _registry(tmp_path, RegisteredSource(
        source_id="SRC-SYN", source_name="Fixture", source_type=SourceType.SYNTHETIC_BENCHMARK,
        classification=DataClassification.SYNTHETIC, permission_status=PermissionStatus.AUTHORIZED, is_demo=True,
    ))
    record = _high_record(1); record["source_id"] = "SRC-SYN"
    report = ReleaseGateAuditor(registry_path=path).audit_dataset_release("sift_dataset", "1.0.0", [record], [record], [], [record, record, record], source_id="SRC-SYN", locked_test_set=True)
    assert not report.is_release_approved
    assert any(g.gate_name == "SOURCE_AUTHORIZATION_AND_PROVENANCE" and not g.passed for g in report.gate_checks)


def test_missing_provenance_and_high_sif_floor_block_release(tmp_path):
    path = _registry(tmp_path, RegisteredSource(
        source_id="SRC-REAL", source_name="Authorized", source_type=SourceType.INTERNAL_SAFETY_REPORTS,
        classification=DataClassification.REAL, permission_status=PermissionStatus.AUTHORIZED,
        record_count=1, collection_date="2026-01-01", raw_file_sha256="b" * 64, authorization_reference="AUTH-1",
    ))
    record = _high_record(1); record.pop("source_id")
    report = ReleaseGateAuditor(registry_path=path).audit_dataset_release("sift_dataset", "1.0.0", [record], [record], [], [], source_id="SRC-REAL", locked_test_set=False)
    failed = {g.gate_name for g in report.gate_checks if not g.passed}
    assert {"SOURCE_AUTHORIZATION_AND_PROVENANCE", "HIGH_SIF_TEST_REPRESENTATION", "LOCKED_TEST_SET"} <= failed


def test_source_id_mismatch_cannot_be_operator_bypassed(tmp_path):
    path = _registry(tmp_path, RegisteredSource(
        source_id="SRC-REAL", source_name="Authorized", source_type=SourceType.INTERNAL_SAFETY_REPORTS,
        classification=DataClassification.REAL, permission_status=PermissionStatus.AUTHORIZED,
        record_count=3, collection_date="2026-01-01", raw_file_sha256="c" * 64, authorization_reference="AUTH-2",
    ))
    records = [_high_record(i) for i in range(3)]
    report = ReleaseGateAuditor(registry_path=path).audit_dataset_release("sift_dataset", "1.0.0", records, [], [], records, source_id="SRC-REAL", locked_test_set=True)
    assert not report.is_release_approved
    assert "do not match" in next(g.details for g in report.gate_checks if g.gate_name == "SOURCE_AUTHORIZATION_AND_PROVENANCE")

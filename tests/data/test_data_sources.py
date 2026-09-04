"""Tests for SIFT Data Source Registry & Provenance Tracking."""

import os
import tempfile
import pytest

from data_pipeline.sources import (
    SourceRegistry,
    RegisteredSource,
    SourceType,
    DataClassification,
    PermissionStatus,
)


def test_source_registry_registration_and_persistence(tmp_path):
    """Verify registering a source saves to JSON and reloads correctly."""
    reg_file = tmp_path / "test_source_registry.json"
    registry = SourceRegistry(registry_path=str(reg_file))

    src = RegisteredSource(
        source_id="SRC-OIL-TEST-01",
        source_name="OIL Upper Assam Drilling Logs",
        source_type=SourceType.INTERNAL_SAFETY_REPORTS,
        classification=DataClassification.REAL,
        permission_status=PermissionStatus.AUTHORIZED,
        data_owner="Oil India Limited HSE Directorate",
        record_count=250,
        collection_date="2026-01-15",
        raw_file_sha256="a" * 64,
        authorization_reference="AUTH-TEST-001",
    )

    registry.register_source(src)
    assert reg_file.exists()

    # Reload from disk
    reloaded = SourceRegistry(registry_path=str(reg_file))
    fetched = reloaded.get_source("SRC-OIL-TEST-01")
    assert fetched is not None
    assert fetched.source_name == "OIL Upper Assam Drilling Logs"
    assert fetched.classification == DataClassification.REAL
    assert fetched.permission_status == PermissionStatus.AUTHORIZED


def test_source_eligibility_validation(tmp_path):
    """Verify eligibility checks reject unauthorized or missing sources."""
    reg_file = tmp_path / "test_source_registry.json"
    registry = SourceRegistry(registry_path=str(reg_file))

    auth_src = RegisteredSource(
        source_id="SRC-AUTH",
        source_name="Authorized Source",
        source_type=SourceType.INTERNAL_SAFETY_REPORTS,
        classification=DataClassification.REAL,
        permission_status=PermissionStatus.AUTHORIZED,
        record_count=1,
        collection_date="2026-01-15",
        raw_file_sha256="a" * 64,
        authorization_reference="AUTH-TEST-001",
    )
    unauth_src = RegisteredSource(
        source_id="SRC-RESTRICTED",
        source_name="Restricted Source",
        source_type=SourceType.INTERNAL_SAFETY_REPORTS,
        classification=DataClassification.REAL,
        permission_status=PermissionStatus.RESTRICTED,
    )

    registry.register_source(auth_src)
    registry.register_source(unauth_src)

    ok, _ = registry.validate_eligibility("SRC-AUTH")
    assert ok is True

    ok_unauth, msg = registry.validate_eligibility("SRC-RESTRICTED")
    assert ok_unauth is False
    assert "must be AUTHORIZED" in msg

    ok_missing, msg2 = registry.validate_eligibility("SRC-NONEXISTENT")
    assert ok_missing is False
    assert "not registered" in msg2


def test_synthetic_or_incomplete_sources_are_never_real_release_eligible(tmp_path):
    reg_file = tmp_path / "sources.json"
    registry = SourceRegistry(registry_path=str(reg_file))
    synthetic = RegisteredSource(
        source_id="SRC-SYN", source_name="Fixture data", source_type=SourceType.SYNTHETIC_BENCHMARK,
        classification=DataClassification.SYNTHETIC, permission_status=PermissionStatus.AUTHORIZED, is_demo=True,
    )
    incomplete = RegisteredSource(
        source_id="SRC-INCOMPLETE", source_name="Real but incomplete", source_type=SourceType.INTERNAL_SAFETY_REPORTS,
        classification=DataClassification.REAL, permission_status=PermissionStatus.AUTHORIZED,
    )
    registry.register_source(synthetic)
    registry.register_source(incomplete)
    assert registry.validate_eligibility("SRC-SYN")[0] is False
    assert registry.validate_eligibility("SRC-INCOMPLETE")[0] is False

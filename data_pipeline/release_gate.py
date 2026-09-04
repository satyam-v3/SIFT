"""SIFT Dataset Release Gate & Pre-Flight Quality Auditor.

Enforces strict criteria before safety datasets can be released for machine learning training:
1. Provenance & source authorization verification
2. Zero unredacted PII & feature/label leakage
3. 100% human annotation completion & zero unresolved adjudications
4. Strict taxonomy v1.0 enumeration validation
5. Exact character-offset evidence span invariance
6. Zero cross-split leakage (event/duplicate grouping)
7. High-SIF representation floor checks
"""

from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from data_pipeline.validation import DatasetValidator
from data_pipeline.governance import PIIDetector, GovernanceChecker
from data_pipeline.sources import SourceRegistry, PermissionStatus
from data_pipeline.manifest import DatasetManifestGenerator


class ReleaseGateCheckItem(BaseModel):
    """Single release gate audit criteria."""
    gate_name: str
    passed: bool
    details: str
    severity: str = "CRITICAL"  # CRITICAL, WARNING, INFO


class ReleaseGateReport(BaseModel):
    """Comprehensive release gate report."""
    dataset_id: str
    dataset_version: str
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_release_approved: bool
    total_records: int
    critical_failures: int
    warnings: int
    gate_checks: List[ReleaseGateCheckItem] = Field(default_factory=list)


class ReleaseGateAuditor:
    """Performs rigorous pre-release quality and governance audits."""

    def __init__(self, taxonomy_version: str = "1.0", registry_path: Optional[str] = None):
        self.taxonomy_version = taxonomy_version
        self.validator = DatasetValidator()
        self.pii_detector = PIIDetector()
        self.gov_checker = GovernanceChecker()
        self.source_registry = SourceRegistry(registry_path) if registry_path else SourceRegistry()

    def audit_dataset_release(
        self,
        dataset_id: str,
        version: str,
        validated_records: List[Dict[str, Any]],
        train_records: Optional[List[Dict[str, Any]]] = None,
        val_records: Optional[List[Dict[str, Any]]] = None,
        test_records: Optional[List[Dict[str, Any]]] = None,
        source_id: Optional[str] = None,
        locked_test_set: bool = False,
        is_demo_release: bool = False,
    ) -> ReleaseGateReport:
        """Run all critical pre-flight gates on candidate release records."""
        checks: List[ReleaseGateCheckItem] = []
        n = len(validated_records)

        # Gate 1: Source is authoritative, real, authorized, and provenance-complete.
        # Never derive source eligibility from an operator-provided classification claim.
        source_ids = {
            r.get("source_id") or r.get("provenance", {}).get("source_id")
            for r in validated_records
        }
        source_ids.discard(None)
        source_ok = False
        source_reason = ""
        if is_demo_release:
            source_reason = "Demo/synthetic releases are not eligible for real dataset release."
        elif not source_id:
            source_reason = "No authoritative source_id supplied for release."
        elif not source_ids:
            source_reason = "Candidate records lack required source provenance."
        elif source_ids != {source_id}:
            source_reason = f"Record provenance source IDs {sorted(source_ids)} do not match requested source '{source_id}'."
        else:
            source_ok, source_reason = self.source_registry.validate_eligibility(source_id)
            source_reason = source_reason or f"Source '{source_id}' is eligible for real release."
        checks.append(ReleaseGateCheckItem(
            gate_name="SOURCE_AUTHORIZATION_AND_PROVENANCE",
            passed=source_ok,
            details=source_reason,
        ))

        # Gate 2: Non-empty dataset
        if n == 0:
            checks.append(ReleaseGateCheckItem(
                gate_name="NON_EMPTY_DATASET",
                passed=False,
                details="Dataset contains 0 records.",
            ))
            return ReleaseGateReport(
                dataset_id=dataset_id,
                dataset_version=version,
                is_release_approved=False,
                total_records=0,
                critical_failures=1,
                warnings=0,
                gate_checks=checks,
            )
        else:
            checks.append(ReleaseGateCheckItem(
                gate_name="NON_EMPTY_DATASET",
                passed=True,
                details=f"Dataset contains {n} records.",
            ))

        # Gate 3: Schema & Evidence Span Invariants
        invalid_schema_count = 0
        invalid_spans_count = 0
        for r in validated_records:
            res = self.validator.validate_record(r)
            if not res.is_valid:
                invalid_schema_count += 1
                if any("Evidence span" in str(e.message) for e in res.errors):
                    invalid_spans_count += 1

        checks.append(ReleaseGateCheckItem(
            gate_name="SCHEMA_AND_SPAN_OFFSETS",
            passed=(invalid_schema_count == 0),
            details=f"Schema failures: {invalid_schema_count}, Span offset errors: {invalid_spans_count}.",
        ))

        # Gate 4: Annotation Resolution Status
        unresolved_count = 0
        valid_statuses = {"CONSENSUS_ACCEPTED", "ADJUDICATED", "APPROVED"}
        for r in validated_records:
            ann = r.get("annotation", {})
            st = ann.get("review_status", "")
            if st not in valid_statuses:
                unresolved_count += 1

        checks.append(ReleaseGateCheckItem(
            gate_name="ANNOTATION_RESOLUTION",
            passed=(unresolved_count == 0),
            details=f"Unresolved / pending records: {unresolved_count} (must be 0).",
        ))

        # Gate 5: Privacy & Governance Audit
        pii_flagged_count = 0
        label_leak_count = 0
        for r in validated_records:
            r_id = r.get("report_id", "UNKNOWN")
            raw_text = r.get("raw_text", "")
            pii_res = self.pii_detector.scan(raw_text)
            if not pii_res.is_clean:
                pii_flagged_count += 1
            gov_res = self.gov_checker.audit_record(r_id, raw_text, r.get("context", {}))
            if not gov_res.passed_governance:
                label_leak_count += 1

        checks.append(ReleaseGateCheckItem(
            gate_name="PRIVACY_AND_GOVERNANCE",
            passed=(pii_flagged_count == 0 and label_leak_count == 0),
            details=f"PII occurrences: {pii_flagged_count}, Feature/Target leakage: {label_leak_count}.",
        ))

        # Gate 6/7: Cross-split isolation and mandatory High-SIF safety floor.
        if train_records is not None and test_records is not None:
            train_texts = {r.get("raw_text", "") for r in train_records}
            test_texts = {r.get("raw_text", "") for r in test_records}
            split_overlap = len(train_texts.intersection(test_texts))
            
            checks.append(ReleaseGateCheckItem(
                gate_name="CROSS_SPLIT_LEAKAGE",
                passed=(split_overlap == 0),
                details=f"Shared narratives between train and test: {split_overlap}.",
            ))

            high_sif_test = sum(
                1 for r in test_records
                if str(r.get("labels", {}).get("sif_potential", "")).upper() in {"CRITICAL", "HIGH"}
            )
            checks.append(ReleaseGateCheckItem(
                gate_name="HIGH_SIF_TEST_REPRESENTATION",
                passed=(high_sif_test >= 3),
                details=(
                    f"High-SIF observations in test split: {high_sif_test} "
                    "(mandatory floor: >= 3)."
                ),
            ))
            checks.append(ReleaseGateCheckItem(
                gate_name="LOCKED_TEST_SET",
                passed=locked_test_set,
                details=("Test split is designated locked and immutable for release." if locked_test_set
                         else "Test split is not marked locked; real dataset release is prohibited."),
            ))
        else:
            checks.append(ReleaseGateCheckItem(
                gate_name="HIGH_SIF_TEST_REPRESENTATION",
                passed=False,
                details="INSUFFICIENT DATA: temporal test split was not supplied.",
            ))
            checks.append(ReleaseGateCheckItem(
                gate_name="LOCKED_TEST_SET",
                passed=False,
                details="INSUFFICIENT DATA: no test split is available to lock.",
            ))

        critical_failures = sum(1 for c in checks if not c.passed and c.severity == "CRITICAL")
        warnings = sum(1 for c in checks if c.severity == "WARNING" or (not c.passed and c.severity != "CRITICAL"))
        approved = (critical_failures == 0)

        return ReleaseGateReport(
            dataset_id=dataset_id,
            dataset_version=version,
            is_release_approved=approved,
            total_records=n,
            critical_failures=critical_failures,
            warnings=warnings,
            gate_checks=checks,
        )

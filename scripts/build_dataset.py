#!/usr/bin/env python3
"""SIFT Master Dataset Engineering & Build Pipeline.

Orchestrates the entire reproducible dataset build lifecycle:
INGESTION -> NORMALIZATION -> VALIDATION -> PII/GOVERNANCE -> DEDUPLICATION -> SPLITTING -> MANIFEST -> QUALITY REPORTS

Usage:
    python scripts/build_dataset.py --source data/raw/source.jsonl --version 1.0.0 --output-dir data/
    python scripts/build_dataset.py --source data/raw/source.jsonl --version 1.0.0 --dry-run
"""

import argparse
from datetime import datetime, timezone
import json
import os
import sys
from typing import Any, Dict, List

# Ensure root and api are in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "api")))

from data_pipeline.ingestion import DataIngester
from data_pipeline.normalization import normalize_text, compute_content_hash
from data_pipeline.governance import GovernanceChecker, PIIStatus
from data_pipeline.validation import DatasetValidator
from data_pipeline.duplicates import DuplicateDetector, DuplicateType
from data_pipeline.splitting import DatasetSplitter, SplitConfig
from data_pipeline.metrics import DatasetMetricsCalculator
from data_pipeline.manifest import (
    DatasetManifestGenerator,
    DatasetMetadata,
    QualityReport,
)
from data_pipeline.release_gate import ReleaseGateAuditor


def run_pipeline(
    source_path: str,
    version: str,
    output_dir: str,
    dataset_id: str = "sift_dataset",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    dry_run: bool = False,
    redact_pii: bool = False,
    is_demo: bool = False,
    source_id: str | None = None,
):
    print("=" * 65)

    if not dry_run and not is_demo and not source_id:
        raise ValueError("A non-demo dataset build requires a registered --source-id and release-gate audit.")
    print(f" SIFT DATASET ENGINEERING PIPELINE - BUILD v{version}")
    print(f" Mode: {'DRY RUN' if dry_run else 'RELEASE BUILD'} | Dataset ID: {dataset_id}")
    print("=" * 65)

    # 1. Ingestion
    print(f"\n[1/7] Ingesting raw records from: {source_path}")
    ingester = DataIngester()
    ingested_records = ingester.ingest_file(source_path)
    print(f"      Found {len(ingested_records)} source records.")

    # 2. Normalization & Preprocessing
    print("\n[2/7] Normalizing raw narratives and verifying offset integrity...")
    normalized_records = []
    for rec in ingested_records:
        if not rec.is_eligible:
            continue
        data = rec.raw_data
        if source_id:
            # Preserve the authoritative source reference with each canonical record.
            data["source_id"] = source_id
        if "raw_text" in data:
            data["raw_text"] = normalize_text(data["raw_text"])
        normalized_records.append(data)
    print(f"      Normalized {len(normalized_records)} eligible records.")

    # 3. Canonical Validation
    print("\n[3/7] Executing canonical validation (Schema, Taxonomy v1.0, Evidence Spans)...")
    validator = DatasetValidator(strict_taxonomy=True)
    valid_records: List[Dict[str, Any]] = []
    invalid_records: List[Dict[str, Any]] = []
    validation_reports: List[Dict[str, Any]] = []

    for r in normalized_records:
        res = validator.validate_record_dict(r)
        validation_reports.append(res.to_dict())
        if res.is_valid:
            valid_records.append(r)
        else:
            invalid_records.append(r)
            print(f"      [FAIL] Record {res.record_id} invalid: {[e.message for e in res.errors]}")

    print(f"      Valid: {len(valid_records)} | Invalid/Rejected: {len(invalid_records)}")

    if len(valid_records) == 0:
        print("\n[x] Build Aborted: Zero valid records found.")
        sys.exit(1)

    # 4. Governance & PII Checks
    print("\n[4/7] Auditing PII compliance and input feature label leakage...")
    gov_checker = GovernanceChecker()
    pii_flagged_count = 0
    clean_records = []

    for r in valid_records:
        r_id = r.get("report_id", "UNKNOWN")
        raw = r.get("raw_text", "")
        ctx = r.get("context", {})
        gov_rep = gov_checker.audit_record(r_id, raw, ctx)
        
        if gov_rep.pii_status != PIIStatus.CLEAN:
            pii_flagged_count += 1
            if redact_pii:
                pii_res = gov_checker.pii_detector.scan(raw, redact=True)
                r["raw_text"] = pii_res.sanitized_text

        clean_records.append(r)

    print(f"      PII Flagged Records: {pii_flagged_count} (Redaction applied: {redact_pii})")

    # 5. Deduplication & Near-Duplicate Grouping
    print("\n[5/7] Executing deduplication and cluster identification...")
    detector = DuplicateDetector(near_duplicate_threshold=0.85)
    dup_results, near_matches = detector.process_corpus(clean_records)
    
    exact_count = sum(1 for res in dup_results.values() if res.duplicate_type == DuplicateType.EXACT_DUPLICATE)
    near_count = sum(1 for res in dup_results.values() if res.duplicate_type == DuplicateType.NEAR_DUPLICATE)
    record_clusters = {r_id: res.cluster_id for r_id, res in dup_results.items()}
    print(f"      Exact Duplicates: {exact_count} | Near-Duplicates: {near_count} | Near Matches: {len(near_matches)}")

    # 6. Temporal & Event-Grouped Splitting
    print("\n[6/7] Partitioning records into Train (70%), Val (15%), Test (15%)...")
    split_config = SplitConfig(
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        random_seed=seed,
    )
    splitter = DatasetSplitter(config=split_config)
    split_res = splitter.split(clean_records, record_clusters=record_clusters)

    print(f"      Train: {len(split_res.train_records)} | Val: {len(split_res.val_records)} | Test: {len(split_res.test_records)}")
    print(f"      High-SIF in Test: {split_res.metrics.test_high_sif_count} ({split_res.metrics.high_sif_test_pct}%)")
    print(f"      Zero-Leakage Invariant: {'PASSED' if split_res.leakage_passed else 'FAILED'}")

    if not split_res.leakage_passed:
        print("\n[x] Build Aborted: Split leakage detected across partition boundaries.")
        sys.exit(1)

    # Non-demo output is a release path and must pass the same authoritative
    # governance gates as scripts/release_dataset.py before any artifacts exist.
    if not dry_run and not is_demo:
        release_report = ReleaseGateAuditor().audit_dataset_release(
            dataset_id=dataset_id,
            version=version,
            validated_records=clean_records,
            train_records=split_res.train_records,
            val_records=split_res.val_records,
            test_records=split_res.test_records,
            source_id=source_id,
            locked_test_set=True,
        )
        if not release_report.is_release_approved:
            raise ValueError(
                "Real dataset build blocked by release gates: " +
                "; ".join(f"{g.gate_name}: {g.details}" for g in release_report.gate_checks if not g.passed)
            )

    # 7. Distribution Metrics & Manifest Generation
    print("\n[7/7] Computing dataset distributions, checksums, and quality reports...")
    overall_stats = DatasetMetricsCalculator.calculate(clean_records)
    train_stats = DatasetMetricsCalculator.calculate(split_res.train_records)
    val_stats = DatasetMetricsCalculator.calculate(split_res.val_records)
    test_stats = DatasetMetricsCalculator.calculate(split_res.test_records)

    quality_rep = QualityReport(
        dataset_version=version,
        dataset_id=dataset_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_records=len(ingested_records),
        valid_records=len(valid_records),
        invalid_records=len(invalid_records),
        duplicates_detected=exact_count,
        near_duplicates_detected=near_count,
        pii_flagged=pii_flagged_count,
        leakage_detected=not split_res.leakage_passed,
        sif_potential_breakdown=overall_stats.sif_potential_distribution,
        high_sif_test_count=split_res.metrics.test_high_sif_count,
        warnings=split_res.metrics.warnings,
    )

    metadata = DatasetMetadata(
        dataset_id=dataset_id,
        version=version,
        taxonomy_version="1.0",
        source_description=f"Ingested from {os.path.basename(source_path)}",
        created_at=datetime.now(timezone.utc).isoformat(),
        total_records=len(clean_records),
        split_strategy="Temporal Stratified Grouping with Event & Duplicate Isolation (70/15/15)",
        random_seed=seed,
        overall_statistics=overall_stats,
        train_statistics=train_stats,
        val_statistics=val_stats,
        test_statistics=test_stats,
        validation_summary={"valid": len(valid_records), "invalid": len(invalid_records)},
        governance_summary={"pii_flagged": pii_flagged_count, "redaction_applied": redact_pii},
        leakage_summary={"leakage_passed": split_res.leakage_passed, "clusters_count": len(set(record_clusters.values()))},
    )

    # Output paths
    prefix = f"{dataset_id}_v{version}"
    splits_dir = os.path.join(output_dir, "splits")
    meta_dir = os.path.join(output_dir, "metadata")
    validated_dir = os.path.join(output_dir, "validated")

    os.makedirs(splits_dir, exist_ok=True)
    os.makedirs(meta_dir, exist_ok=True)
    os.makedirs(validated_dir, exist_ok=True)

    validated_file = os.path.join(validated_dir, f"{prefix}_validated.jsonl")
    train_file = os.path.join(splits_dir, f"{prefix}_train.jsonl")
    val_file = os.path.join(splits_dir, f"{prefix}_val.jsonl")
    test_file = os.path.join(splits_dir, f"{prefix}_test.jsonl")
    manifest_file = os.path.join(meta_dir, f"{prefix}_manifest.json")
    metadata_file = os.path.join(meta_dir, f"{prefix}_metadata.json")
    registry_file = os.path.join(meta_dir, "dataset_registry.json")
    quality_json = os.path.join(meta_dir, "quality_report.json")
    quality_md = os.path.join(meta_dir, "quality_report.md")

    if dry_run:
        print("\n" + "=" * 65)
        print(" [!] DRY RUN COMPLETE - No release split artifacts were written.")
        print("=" * 65)
        print(f"Potential Valid Records: {len(valid_records)}")
        print(f"Potential Train Split:   {len(split_res.train_records)}")
        print(f"Potential Val Split:     {len(split_res.val_records)}")
        print(f"Potential Test Split:    {len(split_res.test_records)}")
        print(f"High-SIF in Test:        {split_res.metrics.test_high_sif_count}")
        return

    # Write files
    with open(validated_file, "w", encoding="utf-8") as f:
        for r in clean_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(train_file, "w", encoding="utf-8") as f:
        for r in split_res.train_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(val_file, "w", encoding="utf-8") as f:
        for r in split_res.val_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(test_file, "w", encoding="utf-8") as f:
        for r in split_res.test_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Generate Manifest
    counts = {
        os.path.basename(validated_file): len(clean_records),
        os.path.basename(train_file): len(split_res.train_records),
        os.path.basename(val_file): len(split_res.val_records),
        os.path.basename(test_file): len(split_res.test_records),
    }
    manifest = DatasetManifestGenerator.generate_manifest(
        dataset_id=dataset_id,
        version=version,
        file_paths=[validated_file, train_file, val_file, test_file],
        base_dir=output_dir,
        record_counts=counts,
        is_demo=is_demo,
    )

    with open(manifest_file, "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))

    with open(metadata_file, "w", encoding="utf-8") as f:
        f.write(metadata.model_dump_json(indent=2))

    DatasetManifestGenerator.update_registry(registry_file, manifest, metadata)

    with open(quality_json, "w", encoding="utf-8") as f:
        f.write(quality_rep.model_dump_json(indent=2))

    md_content = DatasetManifestGenerator.generate_markdown_report(quality_rep, metadata)
    with open(quality_md, "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\n" + "=" * 65)
    print(f" [✓] DATASET BUILD SUCCESSFUL: {dataset_id} (v{version})")
    print("=" * 65)
    print(f" Validated Dataset: {validated_file}")
    print(f" Train Split:       {train_file}")
    print(f" Val Split:         {val_file}")
    print(f" Test Split:        {test_file}")
    print(f" Manifest (SHA256): {manifest_file}")
    print(f" Metadata:          {metadata_file}")
    print(f" Quality Report:    {quality_md}")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Build versioned SIFT ML datasets.")
    parser.add_argument("--source", "-s", required=True, help="Path to input source file (.json, .jsonl, .csv)")
    parser.add_argument("--version", "-v", default="1.0.0", help="Dataset version (default: 1.0.0)")
    parser.add_argument("--dataset-id", default="sift_dataset", help="Dataset identifier (default: sift_dataset)")
    parser.add_argument("--output-dir", "-o", default="data", help="Root data output directory (default: data)")
    parser.add_argument("--train-ratio", type=float, default=0.70, help="Train split ratio (default: 0.70)")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="Val split ratio (default: 0.15)")
    parser.add_argument("--test-ratio", type=float, default=0.15, help="Test split ratio (default: 0.15)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic tie-breaking (default: 42)")
    parser.add_argument("--dry-run", action="store_true", help="Perform validation and quality audits without writing split files")
    parser.add_argument("--redact-pii", action="store_true", help="Apply redaction masks to detected PII in narrative")
    parser.add_argument("--demo", action="store_true", help="Mark dataset as demo/synthetic")
    parser.add_argument("--source-id", help="Registered real source ID; required for non-demo builds")

    args = parser.parse_args()

    ds_id = "sift_demo_dataset" if args.demo else args.dataset_id

    run_pipeline(
        source_path=args.source,
        version=args.version,
        output_dir=args.output_dir,
        dataset_id=ds_id,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
        dry_run=args.dry_run,
        redact_pii=args.redact_pii,
        is_demo=args.demo,
        source_id=args.source_id,
    )


if __name__ == "__main__":
    main()

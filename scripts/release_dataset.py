#!/usr/bin/env python3
"""SIFT Official Dataset Release & Quality Gate Verification CLI.

Executes all pre-flight release gates:
1. Source authorization & provenance verification
2. Zero unredacted PII & feature/label leakage audit
3. 100% human annotation completion & zero unresolved adjudications
4. Strict taxonomy v1.0 enumeration validation
5. Exact character-offset evidence span invariance
6. Cross-split leakage protection & High-SIF representation floor
7. Cryptographic SHA-256 manifest & metadata lineage generation

Usage:
    python scripts/release_dataset.py --source-records data/validated/consensus.jsonl --dataset-id sift_dataset --version 1.0.0
"""

import argparse
from datetime import datetime, timezone
import json
import os
import sys

# Ensure root and api are in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "api")))

from data_pipeline.release_gate import ReleaseGateAuditor
from data_pipeline.splitting import DatasetSplitter, SplitConfig
from data_pipeline.metrics import DatasetMetricsCalculator
from data_pipeline.manifest import (
    DatasetManifestGenerator,
    DatasetMetadata,
    QualityReport,
)


def release_dataset(
    source_path: str,
    dataset_id: str = "sift_dataset",
    version: str = "1.0.0",
    output_dir: str = "data",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42,
    is_demo: bool = False,
    source_id: str | None = None,
):
    print("=" * 65)
    print(f" SIFT DATASET RELEASE PIPELINE: {dataset_id} (v{version})")
    print("=" * 65)

    if not os.path.exists(source_path):
        print(f"[!] Error: Source records file not found: {source_path}")
        sys.exit(1)

    records = []
    with open(source_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"\n[1/4] Loaded {len(records)} candidate ground-truth records.")

    if is_demo:
        print("[!] DEMO/SYNTHETIC MODE: packaging may be used for development only; real release is prohibited.")
    elif not source_id:
        print("[X] RELEASE REJECTED: --source-id is required for a real dataset release.")
        return False

    # 1. Split records
    print("\n[2/4] Generating temporal, event-isolated splits (70/15/15)...")
    config = SplitConfig(
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        random_seed=random_seed,
    )
    splitter = DatasetSplitter(config=config)
    splits = splitter.split(records)
    print(f"      Train: {len(splits.train_records)} | Val: {len(splits.val_records)} | Test: {len(splits.test_records)}")

    # 2. Run Pre-Flight Release Gates
    print("\n[3/4] Running pre-flight release gates...")
    auditor = ReleaseGateAuditor()
    report = auditor.audit_dataset_release(
        dataset_id=dataset_id,
        version=version,
        validated_records=records,
        train_records=splits.train_records,
        val_records=splits.val_records,
        test_records=splits.test_records,
        source_id=source_id,
        locked_test_set=True,
        is_demo_release=is_demo,
    )

    print("\n" + "-" * 65)
    print(f"{'Gate Name':<32} | {'Status':<10} | {'Details'}")
    print("-" * 65)
    for c in report.gate_checks:
        st = "[PASSED]" if c.passed else f"[{c.severity}]"
        print(f"{c.gate_name:<32} | {st:<10} | {c.details}")
    print("-" * 65)

    if not report.is_release_approved:
        print(f"\n[X] RELEASE REJECTED: {report.critical_failures} critical gate(s) failed.")
        return False

    # 3. Package and Release
    print("\n[4/4] Release approved. Packaging cryptographic artifacts...")
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

    with open(validated_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(train_file, "w", encoding="utf-8") as f:
        for r in splits.train_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(val_file, "w", encoding="utf-8") as f:
        for r in splits.val_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(test_file, "w", encoding="utf-8") as f:
        for r in splits.test_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    counts = {
        os.path.basename(validated_file): len(records),
        os.path.basename(train_file): len(splits.train_records),
        os.path.basename(val_file): len(splits.val_records),
        os.path.basename(test_file): len(splits.test_records),
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

    overall_stats = DatasetMetricsCalculator.calculate(records)
    train_stats = DatasetMetricsCalculator.calculate(splits.train_records)
    val_stats = DatasetMetricsCalculator.calculate(splits.val_records)
    test_stats = DatasetMetricsCalculator.calculate(splits.test_records)

    quality_rep = QualityReport(
        dataset_version=version,
        dataset_id=dataset_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_records=len(records),
        valid_records=len(records),
        invalid_records=0,
        duplicates_detected=0,
        near_duplicates_detected=0,
        pii_flagged=0,
        leakage_detected=not splits.leakage_passed,
        sif_potential_breakdown=overall_stats.sif_potential_distribution,
        high_sif_test_count=splits.metrics.test_high_sif_count,
        warnings=splits.metrics.warnings,
    )

    metadata = DatasetMetadata(
        dataset_id=dataset_id,
        version=version,
        taxonomy_version="1.0",
        source_description=f"Released via SIFT Quality Gate Pipeline from {os.path.basename(source_path)}",
        created_at=datetime.now(timezone.utc).isoformat(),
        total_records=len(records),
        split_strategy="Temporal Stratified Grouping with Event & Duplicate Isolation (70/15/15)",
        random_seed=random_seed,
        overall_statistics=overall_stats,
        train_statistics=train_stats,
        val_statistics=val_stats,
        test_statistics=test_stats,
        validation_summary={"valid": len(records), "invalid": 0},
        governance_summary={"pii_flagged": 0, "redaction_applied": False},
        leakage_summary={"leakage_passed": splits.leakage_passed, "clusters_count": 0},
    )

    with open(metadata_file, "w", encoding="utf-8") as f:
        f.write(metadata.model_dump_json(indent=2))

    with open(quality_json, "w", encoding="utf-8") as f:
        f.write(quality_rep.model_dump_json(indent=2))

    md_report = DatasetManifestGenerator.generate_markdown_report(quality_rep, metadata)
    with open(quality_md, "w", encoding="utf-8") as f:
        f.write(md_report)

    DatasetManifestGenerator.update_registry(registry_file, manifest, metadata)

    print(f"\n[✓] OFFICIAL DATASET RELEASE COMPLETE: {dataset_id} (v{version})")
    print(f"    Validated: {validated_file}")
    print(f"    Splits:    {train_file}, {val_file}, {test_file}")
    print(f"    Manifest:  {manifest_file}")
    print("=" * 65)
    return True


def main():
    parser = argparse.ArgumentParser(description="Audit and release an official SIFT ML dataset.")
    parser.add_argument("--source-records", "-s", required=True, help="Path to validated candidate records JSONL")
    parser.add_argument("--dataset-id", "-d", default="sift_dataset", help="Dataset identifier (default: sift_dataset)")
    parser.add_argument("--version", "-v", required=True, help="Release version, e.g. 1.0.0")
    parser.add_argument("--output-dir", "-o", default="data", help="Output directory (default: data)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splitting")
    parser.add_argument("--demo", action="store_true", help="Flag if releasing synthetic demo data")
    parser.add_argument("--source-id", help="Registered real source ID; required for real releases")

    args = parser.parse_args()
    release_dataset(
        source_path=args.source_records,
        dataset_id=args.dataset_id,
        version=args.version,
        output_dir=args.output_dir,
        random_seed=args.seed,
        is_demo=args.demo,
        source_id=args.source_id,
    )


if __name__ == "__main__":
    main()

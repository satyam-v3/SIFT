"""SIFT Dataset Manifest, Cryptographic Hashing & Quality Reporting.

Generates SHA-256 dataset manifests, comprehensive metadata schemas,
dataset registry updates, and human/machine-readable quality reports.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from data_pipeline.metrics import DatasetStatistics


class FileManifestEntry(BaseModel):
    """File entry in dataset manifest."""
    name: str
    relative_path: str
    sha256: str
    record_count: int
    size_bytes: int


class DatasetManifest(BaseModel):
    """Immutable cryptographic dataset manifest."""
    dataset_id: str
    version: str
    taxonomy_version: str = "1.0"
    annotation_protocol_version: str = "1.0"
    schema_version: str = "1.0"
    created_at: str
    data_classification: str = "REAL"
    is_demo: bool = False
    release_status: str = "RELEASED"
    files: List[FileManifestEntry] = Field(default_factory=list)


class DatasetMetadata(BaseModel):
    """Rich dataset lineage and configuration metadata."""
    dataset_id: str
    version: str
    taxonomy_version: str
    source_description: str
    created_at: str
    total_records: int
    split_strategy: str
    random_seed: int
    overall_statistics: DatasetStatistics
    train_statistics: DatasetStatistics
    val_statistics: DatasetStatistics
    test_statistics: DatasetStatistics
    validation_summary: Dict[str, Any]
    governance_summary: Dict[str, Any]
    leakage_summary: Dict[str, Any]


class QualityReport(BaseModel):
    """Overall dataset build quality summary."""
    dataset_version: str
    dataset_id: str
    created_at: str
    source_records: int
    valid_records: int
    invalid_records: int
    duplicates_detected: int
    near_duplicates_detected: int
    pii_flagged: int
    leakage_detected: bool
    sif_potential_breakdown: Dict[str, int]
    high_sif_test_count: int
    warnings: List[str] = Field(default_factory=list)


def compute_file_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file on disk."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


class DatasetManifestGenerator:
    """Generates manifests, metadata files, registry records, and Markdown/JSON quality reports."""

    @staticmethod
    def generate_manifest(
        dataset_id: str,
        version: str,
        file_paths: List[str],
        base_dir: str,
        record_counts: Dict[str, int],
        is_demo: bool = False,
    ) -> DatasetManifest:
        """Create a cryptographic manifest for a set of dataset split files."""
        entries: List[FileManifestEntry] = []
        for fp in file_paths:
            if os.path.exists(fp):
                fname = os.path.basename(fp)
                rel_path = os.path.relpath(fp, base_dir)
                f_hash = compute_file_sha256(fp)
                f_size = os.path.getsize(fp)
                f_count = record_counts.get(fname, 0)
                entries.append(FileManifestEntry(
                    name=fname,
                    relative_path=rel_path,
                    sha256=f_hash,
                    record_count=f_count,
                    size_bytes=f_size,
                ))
        return DatasetManifest(
            dataset_id=dataset_id,
            version=version,
            taxonomy_version="1.0",
            annotation_protocol_version="1.0",
            schema_version="1.0",
            created_at=datetime.now(timezone.utc).isoformat(),
            data_classification="DEMO" if is_demo else "REAL",
            is_demo=is_demo,
            release_status="DEMO_ONLY_NOT_REAL_GROUND_TRUTH" if is_demo else "RELEASED",
            files=entries,
        )

    @staticmethod
    def update_registry(
        registry_path: str,
        manifest: DatasetManifest,
        metadata: DatasetMetadata,
    ):
        """Append or update dataset version record in metadata registry."""
        registry: Dict[str, Any] = {"datasets": []}
        if os.path.exists(registry_path):
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            except Exception:
                registry = {"datasets": []}

        # Filter out existing entry with same version and id if updating
        registry["datasets"] = [
            d for d in registry.get("datasets", [])
            if not (d.get("dataset_id") == manifest.dataset_id and d.get("version") == manifest.version)
        ]

        entry = {
            "dataset_id": manifest.dataset_id,
            "version": manifest.version,
            "taxonomy_version": manifest.taxonomy_version,
            "created_at": manifest.created_at,
            "total_records": metadata.total_records,
            "data_classification": manifest.data_classification,
            "release_status": manifest.release_status,
            "files": [f.model_dump() for f in manifest.files],
        }
        registry["datasets"].append(entry)
        
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

    @staticmethod
    def generate_markdown_report(report: QualityReport, metadata: DatasetMetadata) -> str:
        """Render a clean, human-readable GitHub-flavored Markdown quality report."""
        md = []
        md.append(f"# SIFT Dataset Quality & Lineage Report: `{report.dataset_id}` (v{report.dataset_version})\n")
        md.append(f"**Build Timestamp:** `{report.created_at}`  ")
        md.append(f"**Taxonomy Version:** `{metadata.taxonomy_version}`  ")
        md.append(f"**Random Seed:** `{metadata.random_seed}`  ")
        md.append(f"**Split Strategy:** `{metadata.split_strategy}`\n")
        md.append("---\n")

        md.append("## 1. Executive Quality Summary\n")
        md.append("| Metric | Count / Status | Notes |")
        md.append("| :--- | :--- | :--- |")
        md.append(f"| **Source Records Ingested** | `{report.source_records}` | Initial raw record pool |")
        md.append(f"| **Validated Eligible Records** | `{report.valid_records}` | Passed schema & taxonomy audits |")
        md.append(f"| **Invalid / Rejected Records** | `{report.invalid_records}` | Failed validation checks |")
        md.append(f"| **Exact Duplicates (SHA-256)** | `{report.duplicates_detected}` | Deterministic hash collision |")
        md.append(f"| **Near-Duplicates (Jaccard $\\ge 0.85$)** | `{report.near_duplicates_detected}` | Grouped to prevent cross-split leakage |")
        md.append(f"| **PII Flagged Records** | `{report.pii_flagged}` | Sanitized / Flagged under governance |")
        leak_status = "PASSED (Zero Leakage)" if not report.leakage_detected else "FAILED (Leakage Detected)"
        md.append(f"| **Cross-Split Leakage Check** | **{leak_status}** | Event & duplicate cluster isolation |")
        md.append(f"| **High-SIF Count in Test Split** | `{report.high_sif_test_count}` | Safety-critical evaluation floor |")
        md.append("\n---\n")

        md.append("## 2. Partition Summary\n")
        md.append("| Split | Record Count | CRITICAL/HIGH SIF | High-SIF Ratio |")
        md.append("| :--- | :--- | :--- | :--- |")
        tr_tot = metadata.train_statistics.total_records
        tr_high = metadata.train_statistics.sif_potential_distribution.get("CRITICAL", 0) + metadata.train_statistics.sif_potential_distribution.get("HIGH", 0)
        tr_pct = f"{(tr_high/tr_tot*100):.1f}%" if tr_tot > 0 else "0%"
        md.append(f"| **TRAIN (70%)** | `{tr_tot}` | `{tr_high}` | `{tr_pct}` |")

        v_tot = metadata.val_statistics.total_records
        v_high = metadata.val_statistics.sif_potential_distribution.get("CRITICAL", 0) + metadata.val_statistics.sif_potential_distribution.get("HIGH", 0)
        v_pct = f"{(v_high/v_tot*100):.1f}%" if v_tot > 0 else "0%"
        md.append(f"| **VALIDATION (15%)** | `{v_tot}` | `{v_high}` | `{v_pct}` |")

        te_tot = metadata.test_statistics.total_records
        te_high = metadata.test_statistics.sif_potential_distribution.get("CRITICAL", 0) + metadata.test_statistics.sif_potential_distribution.get("HIGH", 0)
        te_pct = f"{(te_high/te_tot*100):.1f}%" if te_tot > 0 else "0%"
        md.append(f"| **TEST (15%)** | `{te_tot}` | `{te_high}` | `{te_pct}` |")
        md.append("\n---\n")

        md.append("## 3. Categorical Class Distributions\n")
        md.append("### SIF Potential Tier (Overall)\n")
        for k, v in metadata.overall_statistics.sif_potential_distribution.items():
            pct = metadata.overall_statistics.sif_potential_pct.get(k, 0.0)
            md.append(f"- **{k}:** `{v}` ({pct}%)")

        md.append("\n### Precursor Category Multi-Label Distribution\n")
        for k, v in metadata.overall_statistics.precursor_categories_distribution.items():
            md.append(f"- **{k}:** `{v}`")

        md.append("\n### Top Primary Hazards\n")
        for k, v in list(metadata.overall_statistics.primary_hazards_distribution.items())[:6]:
            md.append(f"- **{k}:** `{v}`")

        md.append("\n### Barrier Status Breakdown\n")
        for k, v in metadata.overall_statistics.barrier_statuses_distribution.items():
            md.append(f"- **{k}:** `{v}`")

        if report.warnings:
            md.append("\n---\n")
            md.append("## 4. Pipeline Warnings & Quality Alerts\n")
            for w in report.warnings:
                md.append(f"> [!WARNING]\n> {w}\n")

        return "\n".join(md)

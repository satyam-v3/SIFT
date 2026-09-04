"""Tests for SIFT End-to-End Dataset Build Orchestrator, Manifest Generation, and Checksums."""

import json
import os
import shutil
import tempfile
import pytest

from scripts.build_dataset import run_pipeline


def test_build_dataset_dry_run():
    """Verify that --dry-run validates data and computes metrics without creating release split files."""
    fixture_path = os.path.abspath("data/fixtures/sample_raw_reports.jsonl")
    temp_dir = tempfile.mkdtemp()
    
    try:
        run_pipeline(
            source_path=fixture_path,
            version="0.1.0",
            output_dir=temp_dir,
            dry_run=True,
        )
        
        # Check that no release files were written in temp_dir
        splits_dir = os.path.join(temp_dir, "splits")
        assert not os.path.exists(splits_dir) or len(os.listdir(splits_dir)) == 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_build_dataset_full_release():
    """Verify full end-to-end dataset build creates validated, split, manifest, metadata, and quality reports."""
    fixture_path = os.path.abspath("data/fixtures/sample_raw_reports.jsonl")
    temp_dir = tempfile.mkdtemp()
    
    try:
        run_pipeline(
            source_path=fixture_path,
            version="1.0.0",
            output_dir=temp_dir,
            dataset_id="sift_test_dataset",
            dry_run=False,
            is_demo=True,
        )
        
        # 1. Verify split files exist
        splits_dir = os.path.join(temp_dir, "splits")
        assert os.path.exists(os.path.join(splits_dir, "sift_test_dataset_v1.0.0_train.jsonl"))
        assert os.path.exists(os.path.join(splits_dir, "sift_test_dataset_v1.0.0_val.jsonl"))
        assert os.path.exists(os.path.join(splits_dir, "sift_test_dataset_v1.0.0_test.jsonl"))
        
        # 2. Verify manifest file exists and contains SHA-256 checksums
        meta_dir = os.path.join(temp_dir, "metadata")
        manifest_path = os.path.join(meta_dir, "sift_test_dataset_v1.0.0_manifest.json")
        assert os.path.exists(manifest_path)
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["version"] == "1.0.0"
        assert len(manifest["files"]) >= 3
        assert all("sha256" in item and len(item["sha256"]) == 64 for item in manifest["files"])
        
        # 3. Verify quality report markdown and json exist
        assert os.path.exists(os.path.join(meta_dir, "quality_report.json"))
        assert os.path.exists(os.path.join(meta_dir, "quality_report.md"))
        
        # 4. Verify registry update
        registry_path = os.path.join(meta_dir, "dataset_registry.json")
        assert os.path.exists(registry_path)
        with open(registry_path, "r", encoding="utf-8") as f:
            reg = json.load(f)
        assert any(d["version"] == "1.0.0" for d in reg["datasets"])
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

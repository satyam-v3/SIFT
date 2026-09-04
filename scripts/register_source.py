#!/usr/bin/env python3
"""SIFT Raw Data Source Registration & Audit CLI.

Catalogs acquired safety datasets, computes cryptographic hashes, and validates legal permissions.

Usage:
    python scripts/register_source.py register --source-id SRC-OIL-2026-01 --name "OIL Upper Assam Field Data" --type INTERNAL_SAFETY_REPORTS --classification REAL --permission AUTHORIZED
    python scripts/register_source.py list
"""

import argparse
import json
import os
import sys

# Ensure root and api are in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "api")))

from data_pipeline.sources import (
    SourceRegistry,
    RegisteredSource,
    SourceType,
    DataClassification,
    PermissionStatus,
)


def run_register(args):
    registry = SourceRegistry(args.registry)
    
    sha256 = None
    rec_count = args.records
    if args.raw_file and os.path.exists(args.raw_file):
        sha256 = SourceRegistry.compute_file_sha256(args.raw_file)
        if rec_count == 0:
            with open(args.raw_file, "r", encoding="utf-8") as f:
                rec_count = sum(1 for line in f if line.strip())

    source = RegisteredSource(
        source_id=args.source_id,
        source_name=args.name,
        source_type=SourceType(args.type),
        classification=DataClassification(args.classification),
        license=args.license,
        permission_status=PermissionStatus(args.permission),
        data_owner=args.owner,
        allowed_use=args.allowed_use,
        record_count=rec_count,
        raw_file_sha256=sha256,
        authorization_reference=args.authorization_reference,
        acquisition_method=args.acquisition_method,
        source_version=args.source_version,
        sensitivity_classification=args.sensitivity_classification,
        is_demo=args.demo,
        notes=args.notes,
    )

    registry.register_source(source)
    print(f"[✓] Successfully registered source: {source.source_id} ({source.source_name})")
    print(f"    Classification:    {source.classification.value}")
    print(f"    Permission Status: {source.permission_status.value}")
    print(f"    Record Count:      {source.record_count}")
    if sha256:
        print(f"    Raw SHA-256:       {sha256}")


def run_list(args):
    registry = SourceRegistry(args.registry)
    sources = registry.list_sources()

    print("\n" + "=" * 75)
    print(" SIFT REGISTERED DATA SOURCES CATALOG")
    print("=" * 75)
    if not sources:
        print(" No data sources registered yet.")
    else:
        for s in sources:
            print(f"[{s.source_id}] {s.source_name}")
            print(f"  Type: {s.source_type.value:<25} | Class: {s.classification.value:<10} | Perm: {s.permission_status.value}")
            print(f"  Owner: {s.data_owner:<24} | Records: {s.record_count}")
            print("-" * 75)


def main():
    parser = argparse.ArgumentParser(description="Register and manage SIFT data acquisition sources.")
    parser.add_argument("--registry", default="data/metadata/source_registry.json", help="Path to source_registry.json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Register
    p_reg = subparsers.add_parser("register", help="Register a new data source")
    p_reg.add_argument("--source-id", "-s", required=True, help="Unique source ID, e.g. SRC-OIL-2026-01")
    p_reg.add_argument("--name", "-n", required=True, help="Descriptive name of data source")
    p_reg.add_argument("--type", "-t", default="INTERNAL_SAFETY_REPORTS", choices=[e.value for e in SourceType])
    p_reg.add_argument("--classification", "-c", default="REAL", choices=[e.value for e in DataClassification])
    p_reg.add_argument("--permission", "-p", default="AUTHORIZED", choices=[e.value for e in PermissionStatus])
    p_reg.add_argument("--license", "-l", default="PROPRIETARY_OIL_INTERNAL")
    p_reg.add_argument("--owner", default="Oil India Limited HSE Directorate")
    p_reg.add_argument("--allowed-use", default="SIFT Model Training & Safety Intelligence")
    p_reg.add_argument("--raw-file", help="Path to raw source file to hash")
    p_reg.add_argument("--records", type=int, default=0, help="Initial record count")
    p_reg.add_argument("--notes", help="Optional provenance notes")
    p_reg.add_argument("--authorization-reference", help="Non-secret approval/reference identifier")
    p_reg.add_argument("--acquisition-method", help="How the source was acquired")
    p_reg.add_argument("--source-version", help="Source-system schema/version")
    p_reg.add_argument("--sensitivity-classification", help="Data sensitivity classification")
    p_reg.add_argument("--demo", action="store_true", help="Mark a DEMO or SYNTHETIC source; it cannot support real release")

    # List
    subparsers.add_parser("list", help="List all registered data sources")

    args = parser.parse_args()
    if args.command == "register":
        run_register(args)
    elif args.command == "list":
        run_list(args)


if __name__ == "__main__":
    main()

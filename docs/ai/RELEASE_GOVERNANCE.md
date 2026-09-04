# SIFT Release Governance

No authorized real source currently exists. Therefore **Dataset v1.0 is not released** and the files `sift_demo_dataset_v0.1.0` and `sift_sim_dataset_v0.1.0` are development artifacts only, never real ground truth or evidence of production model performance.

## Source semantics

`REAL` describes a non-demo source that may be considered for a real release; `SYNTHETIC` and `DEMO` are permanently ineligible for a real release. Authorization is separate from classification: an eligible source must be registered, `REAL`, not demo, `AUTHORIZED`, `ACTIVE`, have a non-secret authorization reference, acquisition date, raw-file SHA-256 provenance, and a positive acquired-record count. `SourceRegistry.validate_eligibility()` is the sole real-source predicate.

## Mandatory release gates

Both artifact-writing paths (`scripts/release_dataset.py` and non-demo `scripts/build_dataset.py`) use the release auditor. A real release requires matching per-record source provenance, source eligibility, valid schema/evidence offsets, final human annotation state, PII/leakage clearance, no train/test narrative overlap, at least three HIGH/CRITICAL observations in the test split, and a locked test split. Missing test data is **INSUFFICIENT DATA** and fails; the High-SIF floor is a hard failure.

`--source-id` is required for a non-demo release. CLI claims cannot override source classification held in the registry. Demo packaging may remain useful for development, but cannot become Dataset v1.0, a locked real test set, or a production-performance claim.

## Next dependency

The next step is obtaining a **formally authorized real safety-data source** with provenance. Only then should the project proceed to real data acquisition and calibration annotation; no model training should occur before a legitimate released annotation set exists.

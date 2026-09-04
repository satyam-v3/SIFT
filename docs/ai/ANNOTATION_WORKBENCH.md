# SIFT Annotation Workbench

The Annotation Workbench is the operational interface for collecting human annotations from synthetic demo data and, after formal approval, registered real-world safety sources. It reuses the SIFT React application and FastAPI service; it does not expose model predictions, confidence, or explanations to annotators.

## Roles and workflow

Administrators create batches and create two server-side assignment slots per task. Annotators can list only their own assignments, save only their own drafts, and submit one immutable final annotation. The backend verifies evidence offsets against the source narrative. Once both independent submissions are final, it compares canonical fields, multi-label precursor overlap, and evidence IoU. Lead investigators, HSE managers, and administrators can access the disagreement queue and create an adjudication. Release readiness remains a read-only seven-gate backend audit; no UI operation can mark data released.

The development API resolves identity from `X-User-Id`. This is explicitly development-only and must be replaced with authenticated identity middleware before production deployment.

## API

`/api/v1/annotations` exposes batches, assigned tasks, drafts, final submissions, disagreements, adjudication, taxonomy reference data, agreement quality, and release readiness. The task endpoint strips AI fields and peer annotations for annotators. Adjudication endpoints require a lead role server-side.

## Demo mode and data safety

The workbench labels demo batches as **DEMO DATA — NOT GROUND TRUTH**. Demo seed content is synthetic and must never be released or represented as real-world model performance. Raw source paths and governance internals are not returned by the annotation API.

## Canonical output

Submitted and adjudicated annotations retain protocol/taxonomy versions, evidence offsets, barriers, and multi-label fields in the existing database representation. Dataset export and release remain governed by `data_pipeline/annotations.py` and `data_pipeline/release_gate.py`.

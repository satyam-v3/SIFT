# SIFT AI & Data Specification Suite

Welcome to the formal **AI and Data Specification Suite** for **SIFT (Safety Intelligence & Fatality-risk Tracking)**.

SIFT is an AI-powered Safety Intelligence platform intended for Oil India Limited (OIL) to analyze free-text field safety observations—including Unsafe Acts (UA), Unsafe Conditions (UC), Near Misses, and Incidents—to detect Serious Injury and Fatality (SIF) precursors, diagnose safety barrier failures, map IOGP Life-Saving Rules, extract grounded evidence, and prioritize executive interventions.

---

## 1. Purpose of this Specification

This documentation suite establishes the **definitive data contracts, task registry, taxonomy standards, annotation protocols, model roadmap, evaluation criteria, and runtime contracts** before real-world safety data is collected, annotated, and trained on.

It eliminates ambiguity by formalizing:
- The distinction between **AI Prediction** and **Human-Reviewed Ground Truth**.
- The difference between **SIF Potential** (severity capacity) and **SIF Precursor** (hazard exposure without functioning controls).
- The separation of concerns across **Classification, Extraction, Mapping, Scoring, Retrieval, and Analytics**.
- The schema requirements for dataset serialization, character offset groundings, and evaluation protocols.

---

## 2. Specification Document Map

### 2.1 Architecture & Core Specs
| Document | Purpose | Key Contents |
| :--- | :--- | :--- |
| [**System Architecture**](../architecture/ARCHITECTURE.md) | **System Topology** | Full-stack platform blueprint, services, database, and ML interaction. |
| [**SIFT_AI_DATA_SPEC.md**](../architecture/SIFT_AI_DATA_SPEC.md) | **Master AI & Data Specification** | Problem formulation, core design principles, complete Task Registry (TASK-001 to TASK-013), and end-to-end architecture. |

### 2.2 Datasets & Taxonomies (`docs/ai/datasets/`)
| Document | Purpose | Key Contents |
| :--- | :--- | :--- |
| [**TAXONOMY.md**](datasets/TAXONOMY.md) | **Canonical Taxonomies (v1.0)** | Controlled vocabularies for SIF Potential, SIF Precursors, Hazards, Activities, Life-Saving Rules, and Safety Barriers. |
| [**DATASET_CARD.md**](datasets/DATASET_CARD.md) | **Dataset Card (v0.1.0)** | Demographic properties, label distributions, split proportions, and synthetic generation methodology. |
| [**DATASET_SCHEMA.md**](datasets/DATASET_SCHEMA.md) | **Dataset & Record Specification** | Field-by-field JSONL schema dictionary, character-level offset constraints, and data validation rules. |
| [**ANNOTATION_GUIDELINES.md**](datasets/ANNOTATION_GUIDELINES.md) | **Human Annotation Protocol** | Standard operating procedures for annotators, double-blind adjudication, inclusion/exclusion rules, and span offset extraction. |
| [**DATA_ACQUISITION.md**](datasets/DATA_ACQUISITION.md) | **Source Ingestion & Registry** | Guidelines for frontline report ingestion, source registration, and deduplication. |
| [**DATA_VERSIONING.md**](datasets/DATA_VERSIONING.md) | **Data Lineage & Lifecycle** | Dataset naming conventions, taxonomy versioning policies, Model Card standards, and continuous retraining triggers. |

### 2.3 Models & Inference (`docs/ai/models/`)
| Document | Purpose | Key Contents |
| :--- | :--- | :--- |
| [**MODEL_SPECIFICATION.md**](models/MODEL_SPECIFICATION.md) | **Modeling Roadmap & Strategy** | Staged progression from classical NLP baselines to fine-tuned Transformers, structured LLMs, and Hybrid RAG pipelines. |
| [**INFERENCE_CONTRACT.md**](models/INFERENCE_CONTRACT.md) | **Runtime Serving & API Contract** | FastAPI request/response contracts, latency budgets, calibrated confidence, baseline heuristic urgency formulas, and auditability. |
| [**TASK_001_BASELINE.md**](models/TASK_001_BASELINE.md) | **Stage 1 Baseline Runbook** | TF-IDF + Logistic Regression / SVM baseline training, evaluation, and inference. |
| [**TASK_001_TRANSFORMER.md**](models/TASK_001_TRANSFORMER.md) | **Stage 2 Transformer Benchmark** | Fine-tuned DistilBERT transformer encoder benchmark, tokenizer, and comparative evaluation. |
| [**TASK_001_SIF_CLASSIFIER_MODEL_CARD.md**](models/TASK_001_SIF_CLASSIFIER_MODEL_CARD.md) | **Baseline Model Card** | Metadata, operational limits, evaluation performance, and ethics review for classical baseline. |
| [**TASK_001_TRANSFORMER_MODEL_CARD.md**](models/TASK_001_TRANSFORMER_MODEL_CARD.md) | **Transformer Model Card** | Model card for fine-tuned transformer classifier checkpoint. |

### 2.4 Pipelines & Workflows (`docs/ai/pipelines/`)
| Document | Purpose | Key Contents |
| :--- | :--- | :--- |
| [**DATA_PIPELINE.md**](pipelines/DATA_PIPELINE.md) | **Data Pipeline Specification** | Ingestion, sanitization, governance, deduplication, and split generation architecture. |
| [**REAL_DATA_WORKFLOW.md**](pipelines/REAL_DATA_WORKFLOW.md) | **Operational Annotation Workflow** | End-to-end lifecycle for double-blind human annotation, adjudication, and dataset release gates. |
| [**RELEASE_GOVERNANCE.md**](RELEASE_GOVERNANCE.md) | **Real-release governance** | Authoritative real-source eligibility and hard release gates. |

### 2.5 Experiments & Benchmarks (`docs/experiments/`)
| Document | Purpose | Key Contents |
| :--- | :--- | :--- |
| [**EVALUATION_PROTOCOL.md**](../experiments/EVALUATION_PROTOCOL.md) | **Benchmarking & Metrics** | Task-by-task metrics, High-SIF recall prioritization, leakage-free split strategies, and mandatory False Negative root-cause analysis. |

---

## 3. Core Architectural Principles

1. **Dual Classification & Full Auditability**:
   Original AI predictions (`ai_*` fields) are immutable and must **never** be overwritten. Certified HSE safety officer validation sign-offs (`final_*` fields) are recorded alongside reviewer IDs, timestamps, and notes.
2. **Grounded Explainability**:
   Every SIF classification and barrier diagnosis must be supported by an **exact textual evidence phrase** copied directly from the report text. The model must not invent unsupported facts.
3. **Potential over Actual Outcome**:
   A near miss with zero physical injury can still possess **CRITICAL SIF Potential** if high-energy hazards were released in the absence of functioning barriers. SIF potential measures the *capacity of the event to kill or permanently disable*, not the historical outcome.
4. **Controlled Vocabulary & Versioning**:
   All labels must strictly adhere to versioned taxonomies (e.g. `Taxonomy v1.0`). Free-form model outputs must be mapped to discrete categorical IDs.

---

## 4. Code Artifacts & Pydantic Schema Integration

The formal Python Pydantic v2 schemas mirroring this specification reside in:
- [`api/app/schemas/ai/taxonomy.py`](../../api/app/schemas/ai/taxonomy.py): Strongly-typed taxonomy enums and validation classes.
- [`api/app/schemas/ai/dataset.py`](../../api/app/schemas/ai/dataset.py): Canonical JSONL dataset record models with span offset validation.
- [`api/app/schemas/ai/contract.py`](../../api/app/schemas/ai/contract.py): AI model inference input/output schemas, confidence breakdowns, and explainability artifacts.

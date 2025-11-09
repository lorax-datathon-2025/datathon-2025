# datathon-2025

RegDoc is an AI-powered document classification and compliance system that automatically identifies sensitive, confidential, and unsafe content in uploaded files.  
It leverages a multi-stage prompt-based pipeline defined in `prompt_library.yaml` to classify materials according to organizational or regulatory standards.

---

## Overview

RegDoc Guard analyzes text and images from documents and applies one of four classification categories:

| Category | Description |
|-----------|--------------|
| **Public** | Safe for unrestricted external sharing. Contains no personal data, confidential details, or restricted technical information. |
| **Confidential** | Internal or partner-only content (e.g., manuals, training materials, SOPs, internal reports). |
| **Highly Sensitive** | Contains PII, authentication data, or legally restricted content (ITAR/classified/proprietary). |
| **Unsafe** | Contains prohibited or harmful material (violence, hate advocacy, criminal instruction, etc.). |

The classification hierarchy follows a strict **severity ladder**:  
**Highly Sensitive → Confidential → Public**, with “Unsafe” applied as a parallel safety flag.

---

## Key Features

 **Multistage classification pipeline**  
Runs image analysis → text summarization → PII detection → unsafe content scan → confidentiality mapping → final decision synthesis.  

 **YAML-driven policy configuration**  
All prompts, roles, and rules are defined in `prompt_library.yaml`, making the system transparent, auditable, and customizable.

 **Explainable results**  
Every classification includes:
- Supporting citations (page-level snippets)
- Detected features (PII, unsafe text)
- Rationale and confidence score

 **Image-aware analysis**  
Scans embedded diagrams, IDs, and schematics for restricted or unsafe visual content.

 **Structured JSON output**  
Machine-readable results ready for dashboards or downstream compliance tools.

---

## Repository Structure
```plaintext
DATATHON-2025/
├── app/                           # Core backend logic
│   ├── __init__.py
│   ├── db.py                      # Database connection and query helpers
│   ├── detectors.py               # Runs PII, safety, and confidentiality detection
│   ├── hitl.py                    # Human-in-the-loop review & approval
│   ├── job_processor.py           # Queues and manages classification jobs
│   ├── llm_client.py              # API client for primary LLM
│   ├── main.py                    # FastAPI entrypoint / orchestrator
│   ├── models.py                  # Pydantic models and data schemas
│   ├── orchestrator.py            # Main coordinator for multi-step pipelines
│   ├── prompt_lib.py              # Centralized prompt templates
│   ├── secondary_llm.py           # Secondary / fallback model handler
│   ├── storage.py                 # Local or cloud storage integration
│   └── utils_text.py              # Text cleaning, tokenization, summarization utils
│
├── config/
│   └── prompt_library.yaml        # YAML prompt templates & classification policy
│
├── data/                          # Example datasets or test files
│
├── frontend/
│   └── fastapi/                   # FastAPI-based frontend UI and REST endpoints
│
├── test/                          # Unit and integration tests
│   └── __init__.py
│
├── .env                           # Environment variables (API keys, DB URI)
├── .gitignore
├── README.md                      # This documentation
└── requirements.txt               # Python dependencies
```

---

## Architecture

### Ingestion Layer (`db.py`, `storage.py`)
- Uploads `.pdf`, `.docx`, `.txt`, or images.
- Extracts and stores document metadata.

### Text & Image Preprocessing (`utils_text.py`)
- Splits and cleans text.  
- Prepares content for each LLM stage.

### Multi-LLM Orchestration (`orchestrator.py`, `llm_client.py`, `secondary_llm.py`)
- Sequentially triggers all prompt stages defined in YAML.
- Aggregates results with confidence weighting.

### Detection Layer (`detectors.py`)
- PII detection → *Highly Sensitive*  
- Unsafe content → `is_unsafe = true`  
- Confidentiality mapping → *Public*, *Confidential*, or *Highly Sensitive*

### Human-in-the-Loop (`hitl.py`)
- Allows reviewers to confirm or override model classifications.

### FastAPI Frontend (`frontend/fastapi`)
- Provides a RESTful API and web UI for uploading documents and viewing results.  
- Routes include `/upload`, `/analyze`, `/status/{job_id}`, and `/results`.

---

## YAML Policy (v2)

All classification prompts and logic live in `config/prompt_library.yaml`.

Example rule section:

```yaml
rules:
  - match:
      - "manual"
      - "standard operating procedure"
      - "training"
      - "safety management system"
      - "maintenance procedure"
      - "emergency response plan"
      - "security procedures"
    category: "Confidential"
    reason: "Contains non-public operational or procedural guidance intended for internal or partner use."

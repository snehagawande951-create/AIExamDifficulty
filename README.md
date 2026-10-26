# AI-Based Automatic Question Paper Difficulty Analyzer

> **Using Natural Language Processing and Bloom’s Taxonomy Classification**  
> *A research-grade, production-engineered platform for cognitive demand evaluation and empirical examination paper difficulty analysis.*

---

## 1. Project Overview

**Automatic Question Paper Difficulty Analyzer** is an end-to-end NLP system designed to analyze university and higher-secondary examination question papers. The platform parses digital examination documents (PDF and Word `.docx`), segments and identifies individual questions, classifies each question across the **6 revised Bloom’s Taxonomy cognitive levels**, estimates **question difficulty** (Easy, Medium, Hard), and generates auditable institutional analytics and downloadable reports.

### Key Tenets
- **Zero Mock Data in Production:** All dashboard statistics, classifications, and reports originate from real database records, verified model outputs, and genuine documents. Empty states are explicitly rendered when no records exist.
- **Cognitive Level $\ne$ Question Difficulty:** Bloom's cognitive demand and empirical difficulty are treated as two separate classification tasks with independent targets and feature sets.
- **Three-Role Access Control (RBAC):** Distinct capability boundaries for **Admin**, **Teacher/Faculty**, and **Researcher**, with strict tenant isolation preventing cross-user paper leakage.
- **Research Rigor:** Models are evaluated on held-out test splits with Macro-F1, Confusion Matrices, and ablation studies to ensure reproducible academic validity.

---

## 2. System Architecture

```
                          [ Client Browser ]
                                  │
                                  ▼
                [ Frontend: Next.js + React 19 + TypeScript ]
                  • Glassmorphic UI with responsive design tokens
                  • Role-specific dashboards (Admin, Teacher, Researcher)
                  • Interactive question review & manual correction tables
                                  │
                                  │ REST / JSON (Typed Pydantic Contracts)
                                  ▼
                [ Backend: FastAPI (Python 3.11) ]
   ├── Core Security & RBAC (Argon2id hashing, JWT sessions)
   ├── Document Extraction Pipeline (PyMuPDF for PDF, python-docx for DOCX)
   ├── ML Inference Engine (Versioned pickled/ONNX artifacts)
   │     ├── Task A: Bloom's Taxonomy Classifier (6 Cognitive Levels)
   │     └── Task B: Question Difficulty Classifier (Easy / Medium / Hard)
   ├── Report Generator (ReportLab PDF & streaming CSV)
   └── SQLAlchemy 2.0 ORM + Alembic Migrations
                                  │
                                  ▼
         [ Database: SQLite (Dev) / PostgreSQL (Prod) ]
```

---

## 3. Mandatory User Roles

| Role | Core Capabilities | Security & Access Constraints |
| :--- | :--- | :--- |
| **Admin** | User lifecycle (activate/deactivate), audit logs, model deployment config, failure logs. | No public registration; provisioned via CLI setup script; zero credential exposure. |
| **Teacher / Faculty** | Upload papers, review extracted questions/marks, run ML inference, edit predictions, export reports. | Strict ownership isolation; cannot view or mutate another faculty member's documents. |
| **Researcher** | Access authorized research datasets, benchmark models, view confusion matrices & Macro-F1 metrics. | Cannot modify users, alter security policies, or tune against locked held-out test splits. |

---

## 4. Directory Structure

```
├── .gitignore                    # Comprehensive ignores for Python, Node, data & models
├── README.md                     # Architecture, setup guide, and documentation
├── backend/                      # FastAPI Python Application
│   ├── .env.example              # Sample environment configuration
│   ├── requirements.txt          # Audited Python dependencies
│   ├── app/
│   │   ├── main.py               # FastAPI entry point & CORS configuration
│   │   ├── core/
│   │   │   └── config.py         # Pydantic Settings & environment validation
│   │   ├── api/v1/
│   │   │   ├── api.py            # API Router aggregator
│   │   │   └── endpoints/
│   │   │       └── health.py     # Health & diagnostic check endpoint
│   │   └── schemas/
│   │       └── health.py         # Pydantic response models
│   ├── tests/
│   │   ├── conftest.py           # Shared test fixtures (FastAPI TestClient)
│   │   └── test_health.py        # Automated test suite for health & CORS
│   ├── uploads/                  # Secure staging directory for uploaded papers
│   └── reports/                  # Generated PDF & CSV reports directory
├── frontend/                     # Next.js 16 + React 19 + TypeScript Application
│   ├── package.json              # Next.js, React, Recharts, Lucide-react
│   ├── tsconfig.json             # Strict TypeScript configuration
│   └── src/
│       └── app/
│           ├── globals.css       # Obsidian & Cosmic Violet design tokens
│           ├── layout.tsx        # Root HTML layout & metadata
│           └── page.tsx          # Phase 2 Foundation & live diagnostics dashboard
├── data/
│   ├── raw/                      # Original, immutable datasets & sample papers
│   ├── interim/                  # Cleaned & normalized text records
│   └── processed/                # Stratified train/val/test splits
├── docs/                         # Research documentation, guidelines, protocol
├── models/
│   ├── registry/                 # Versioned model artifacts (v1.0.0, etc.)
│   └── baselines/                # TF-IDF, Logistic Regression, Linear SVM baselines
├── research/                     # Jupyter notebooks & exploratory analysis scripts
└── scripts/                      # Automation scripts (admin provisioning, ingestion)
```

---

## 5. Development Setup & Quickstart

### Prerequisites
- **Python**: 3.11+
- **Node.js**: v20+ (v22 tested)
- **Git**: Installed and initialized

### Backend Setup
1. Activate the virtual environment:
   ```powershell
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   ```
2. Verify / install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Run automated tests:
   ```bash
   python -m pytest backend/tests -v
   ```
4. Start the FastAPI development server:
   ```bash
   python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   Interactive OpenAPI Documentation will be available at: `http://127.0.0.1:8000/docs`.

### Frontend Setup
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Start the Next.js development server:
   ```bash
   npm run dev
   ```
3. Open `http://localhost:3000` in your browser. The dashboard will automatically connect to `http://127.0.0.1:8000/api/v1/health` and display live system diagnostics.

---

## 6. Implementation Progression Tracker

- [x] **Phase 1: Requirements and Environment Discovery** — Hardware audited (8GB RAM, Intel UHD), scope locked, zero-mock policy defined.
- [x] **Phase 2: Repository and Application Foundation** — Git configured, FastAPI backend initialized with test suite, Next.js frontend built and verified.
- [x] **Phase 3: Database and Authentication** — SQLAlchemy models, Alembic migrations, Argon2id hashing, JWT auth, and 3-role RBAC.
- [x] **Phase 4: Dataset Pipeline** — Real educational datasets acquired, validated, preprocessed, and stratified.
- [x] **Phase 5: Baseline NLP and ML** — TF-IDF + Logistic Regression / Linear SVM models trained and evaluated.
- [x] **Phase 6: Advanced Modeling** — Compact transformer / feature ablation evaluations, leakage analysis, and error audits.
- [x] **Phase 7: Document Processing Pipeline** — PDF / DOCX text extraction, question number parsing, section segmentation.
- [x] **Phase 8: Backend Integration** — End-to-end APIs for upload, analysis, corrections, and reporting (ReportLab PDF & streaming CSV).
- [x] **Phase 9: Role-Specific Frontend Dashboards** — Admin, Teacher, and Researcher complete interactive views.
- [x] **Phase 10: Integration & Security Testing** — Automated acceptance testing across authorization boundaries.
- [x] **Phase 11: Deployment & Production Hardening** — Production configuration and backup strategy.
- [x] **Phase 12: Research Publication Manuscript** — Experimental findings, confusion matrices, and paper draft.

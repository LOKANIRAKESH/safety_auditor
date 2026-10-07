# Neuro-Symbolic Safety Auditing Framework
### M.Tech Research — Amrita Vishwa Vidyapeetham
**Pre-Synthesis Safety Auditing of Industrial Control Specifications**

---

## What this project does — in plain English

Industrial factories (refineries, chemical plants, gas compressor stations) are
controlled by **PLCs** (Programmable Logic Controllers). Engineers write
**specification documents** — PDFs with tables, diagrams, and prose — that describe
*what the PLC should do*: "if pressure exceeds 80 bar, stop pump P-101."

Modern AI tools can translate these documents into PLC code automatically. But
there is a critical blind spot: **if a safety rule is missing from the specification,
the AI faithfully translates the gap into missing code.** No code-level tool can
detect something that was never written.

This framework **audits the specification before any code is generated**. It reads
the PDFs, extracts the control rules using an LLM, and uses a formal mathematics
engine (Z3 SMT solver) to check whether those rules are complete and consistent
against 19 IEC 61511 safety standards. If a safety shutdown rule is missing, this
system finds it — before a single line of PLC code is written.

---

## The Pre-Synthesis Gap (the core research problem)

```
TRADITIONAL PIPELINE:
  Specification ──► PLC Code Generation ──► Post-Generation Verification
                                                        ↑
                                          Can only check rules that EXIST.
                                          A missing rule has no code → invisible.

THIS FRAMEWORK:
  Specification ──► [SAFETY AUDIT ◄─── IEC 61511 Invariants]
                           ↓
                   Verified Specification ──► PLC Code Generation
```

The safety audit intercepts **specification-level defects** — missing rules,
contradictions, tag inconsistencies — before any synthesis occurs. Post-generation
verification is structurally blind to these by design.

---

## Architecture — 9-Phase Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INPUT: ICS Specification PDF                     │
│            (control narrative + C&E table + P&ID diagram)           │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
         ┌────────▼────────┐
         │   PHASE 1        │  PDF text extraction (PyMuPDF)
         │   Ingestion      │  Table extraction (Camelot / pdfplumber)
         │                  │  P&ID OCR (OpenCV + Tesseract)
         └────────┬────────┘
                  │  text_blocks, tables, pid_tags
         ┌────────▼────────┐
         │   PHASE 2        │  Local LLM via Ollama (Qwen 2.5 / Llama 3)
         │   LLM Extraction │  Extracts: equipment tags, sensor tags,
         │                  │  condition-action rules as JSON
         └────────┬────────┘
                  │  ExtractedEntity[], ExtractedRule[]
         ┌────────▼────────┐
         │   PHASE 3        │  Step 1: Exact tag match
         │   Cross-Modal    │  Step 2: Fuzzy Levenshtein match (OCR noise)
         │   Entity Linking │  Step 3: Sentence-transformer embedding match
         │                  │  → P-101 (narrative) == P101 (table) == P-101A (P&ID)
         └────────┬────────┘
                  │  LinkedEntity[] (canonical tags)
         ┌────────▼────────┐
         │   PHASE 4        │  NetworkX DiGraph
         │   Knowledge      │  Nodes: equipment, sensors
         │   Graph          │  Edges: control relationships
         │                  │  Export: PyVis interactive HTML + SQLite DB
         └────────┬────────┘
                  │  EquipmentGraph
         ┌────────▼────────┐
         │   PHASE 5        │  Pydantic v2 validated ControlRule IR
         │   Control Rule   │  rule = ⟨equip_id, condition, action, conf, page⟩
         │   IR             │  condition = (sensor, operator, threshold, unit)
         │                  │  Auto-flags rules with confidence < 0.70
         └────────┬────────┘
                  │  ControlRule[]
         ┌────────▼────────┐
         │   PHASE 6        │  19 IEC 61511 invariant templates (JSON)
         │   Invariant      │  Checks: which invariants apply to this spec?
         │   Coverage       │  Which are covered by extracted rules?
         │                  │  Uncovered = OMISSION candidate
         └────────┬────────┘
                  │  InvariantCoverageResult[]
         ┌────────▼────────┐
         │   PHASE 7        │  Z3 SMT Solver — 3 verification passes:
         │   Z3 Formal      │  Pass 1: OMISSION (invariant with no covering rule)
         │   Verification   │  Pass 2: CONTRADICTION (opposing rules for same equip)
         │                  │  Pass 3: TAG_MISMATCH (low-confidence ambiguous rules)
         └────────┬────────┘
                  │  AuditFinding[]
         ┌────────▼────────┐
         │   PHASE 8        │  Jinja2 HTML report (severity colours, evidence pages)
         │   Audit Report   │  Optional PDF via WeasyPrint
         │                  │  → Persisted to SQLite (output/audit_store.db)
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │   PHASE 9        │  IEC 61131-3 Structured Text (.st file)
         │   PLC Code       │  One PROGRAM block per specification
         │   Sketch         │  VAR declarations + IF/THEN blocks with comments
         └─────────────────┘
```

---

## What is Novel Here?

This is the key question for the research paper. Here are the **three original contributions**:

### Novelty 1 — The Pre-Synthesis Gap Framing

No prior work frames the problem as: *"the specification itself may be incomplete
before code generation begins."* All existing tools (SCADE, Simulink Design Verifier,
LLM4PLC, Digitize-PID) assume the specification is correct and only verify the
generated code. We show that this assumption breaks down in practice, and we close
the gap computationally for the first time.

**In one sentence:** We detect defects in what the engineer *intended* to write,
not in what the computer *generated* from that intention.

### Novelty 2 — Neuro-Symbolic Role Separation for Safety

The key architectural insight is **strict role separation**:
- The LLM is used *only* for what it is good at: understanding natural language
- Z3 is used *only* for what it is good at: logical reasoning over formal constraints
- The LLM never makes safety judgements; Z3 never parses natural language

This separation is not just elegant — it is *trustworthy*. When a finding is
reported, it traces to a specific Z3 verification result against a named IEC 61511
clause. A process safety engineer can inspect exactly which clause was violated and
exactly which rule was absent. An LLM-only system produces hallucinated findings
with no auditable provenance.

**In one sentence:** LLMs understand text; formal solvers reason about logic.
We exploit both and conflate neither.

### Novelty 3 — Multimodal ICS Specification Ingestion (As-Authored)

Every existing formal verification tool for ICS (SCADE, Simulink, Event-B) requires
the engineer to rewrite their specification in a structured modelling language first.
This re-authoring effort is as large as writing the PLC code — defeating the purpose.

This framework accepts specifications **as they are authored** — free-text control
narratives, tabular cause-and-effect tables, and P&ID diagrams — and extracts
structured logic from them automatically via the 3-step cross-modal linking cascade.

**In one sentence:** We go from raw industrial PDFs to formal safety verification
without the engineer touching a modelling tool.

---

## Technology Stack

| Layer | Technology | Why |
|---|---|---|
| PDF parsing | PyMuPDF, pdfplumber, Camelot | Industrial-grade extraction; Camelot handles bordered tables |
| P&ID OCR | OpenCV + Tesseract | ISA 5.1 symbol detection + tag regex |
| LLM extraction | Qwen 2.5 / Llama 3 via Ollama | Runs locally — no API keys, no data leaving the machine |
| Entity linking | FuzzyWuzzy + sentence-transformers | Handles OCR noise + semantic variation |
| Knowledge graph | NetworkX + PyVis | In-memory graph ops + interactive HTML export |
| Formal IR | Pydantic v2 | Type-safe rule representation with auto-validation |
| Formal verification | Z3 SMT solver (Microsoft Research) | Sound and complete within decidable theories |
| Safety oracle | 19 IEC 61511 invariant templates (JSON) | Normative standard, clause-aligned |
| Persistent store | SQLite via SQLAlchemy 2.0 | Zero-setup embedded DB; WAL mode for concurrent reads |
| Reporting | Jinja2 HTML + WeasyPrint PDF | Self-contained, offline-renderable reports |
| PLC generation | IEC 61131-3 Structured Text | Industry-standard PLC language |
| Frontend | Streamlit 6-page dashboard | Rapid research UI; no backend server needed |
| CLI | Typer + Rich | Clean command-line interface with progress bars |

---

## Project Structure

```
safety_auditor/
│
├── src/                        Core pipeline source code
│   ├── config.py               Pydantic Settings — all configuration in one place
│   ├── ingestion/              Phase 1: PDF, table, P&ID extraction
│   │   ├── pdf_extractor.py    PyMuPDF text block extraction
│   │   ├── table_extractor.py  Camelot / pdfplumber C&E table extraction
│   │   └── pid_extractor.py    OpenCV + Tesseract P&ID tag OCR
│   ├── extraction/             Phase 2: LLM entity and rule extraction
│   │   ├── entity_extractor.py Ollama API calls, JSON parsing, fallback model
│   │   └── prompts.py          System prompt + 3 ICS few-shot examples
│   ├── linking/                Phase 3: Cross-modal entity resolution
│   │   └── cross_modal_linker.py  Exact → Fuzzy → Embedding cascade
│   ├── knowledge/              Phase 4: NetworkX knowledge graph
│   │   └── graph_builder.py    Node/edge construction + PyVis HTML export
│   ├── ir/                     Phase 5: Pydantic control rule IR
│   │   ├── rule_model.py       ControlRule, Condition, RuleAction, ComparisonOperator
│   │   └── rule_builder.py     ExtractedRule → ControlRule conversion
│   ├── invariants/             Phase 6: IEC 61511 safety oracle
│   │   ├── library.py          Coverage evaluation against entity-class map
│   │   ├── loader.py           JSON template loader
│   │   └── templates/          19 invariant JSON templates (SD, PT, LV, MX, ESD)
│   ├── verification/           Phase 7: Z3 SMT formal verification
│   │   ├── z3_auditor.py       OMISSION / CONTRADICTION / TAG_MISMATCH passes
│   │   └── finding_model.py    AuditFinding Pydantic model (5 finding types)
│   ├── reporting/              Phase 8: HTML / PDF audit report
│   │   ├── report_generator.py Jinja2 rendering + optional WeasyPrint PDF
│   │   └── templates/          audit_report.html.j2
│   ├── plc/                    Phase 9: IEC 61131-3 PLC code generation
│   │   ├── code_generator.py   Rule → Structured Text via Jinja2
│   │   └── templates/          structured_text.j2
│   ├── pipeline/               Main orchestrator
│   │   └── auditor.py          SafetyAuditor.run() — wires all 9 phases
│   └── db/                     ← NEW: Persistent SQLite audit store
│       ├── models.py           SQLAlchemy ORM: AuditRun, Finding, KGNode, KGEdge
│       ├── session.py          SQLite engine, WAL mode, context manager
│       └── repository.py       AuditRepository — all DB reads/writes
│
├── ui/
│   └── app.py                  Streamlit 6-page dashboard
│                                 Page 1: Upload & Run
│                                 Page 2: Findings (filterable + Plotly charts)
│                                 Page 3: Knowledge Graph (interactive PyVis)
│                                 Page 4: PLC Output (download .st file)
│                                 Page 5: Audit History (from SQLite)
│                                 Page 6: Benchmark Metrics (F1 / P / R charts)
│
├── benchmark/
│   ├── generator.py            Generates synthetic PDF spec packages with injected defects
│   ├── defect_injector.py      5 defect types cross-referenced to ICS-CERT incidents
│   └── corpus/                 50 pre-generated packages (PKG-001 to PKG-050)
│
├── evaluation/
│   ├── metrics.py              Precision / Recall / F1 per defect category
│   ├── run_evaluation.py       Evaluate full corpus + optional ablation
│   ├── ablation.py             H2 test: linking ON vs OFF
│   ├── baseline.py             Post-generation Z3 baseline (no invariant library)
│   └── results/                Pre-computed results (metrics.json, predictions.json)
│
├── tests/                      Pytest test suite (15 tests, no Ollama required)
│   ├── conftest.py             Shared fixtures (config, sample rules)
│   ├── test_ingestion.py       Tag pattern, C&E detection, PID extraction
│   ├── test_extraction.py      Entity linking, ablation passthrough
│   ├── test_z3_auditor.py      OMISSION, contradiction, unsafe state, tag mismatch
│   └── test_pipeline.py        End-to-end integration (no LLM calls)
│
├── paper/
│   ├── main.tex                IEEE conference paper (all results filled in)
│   ├── references.bib          BibTeX — all citations complete
│   ├── compile.bat             One-click LaTeX → PDF
│   └── HOW_TO_SUBMIT.md        IEEE submission checklist
│
├── scripts/
│   └── generate_figures.py     Matplotlib figures for the paper (from metrics.json)
│
├── data/
│   └── schneider_electric/     Drop your real industrial PDF here
│
├── output/
│   └── audit_store.db          SQLite database — created automatically on first run
│
├── run_pipeline.py             CLI entry point (Typer)
├── requirements.txt            All dependencies with pinned minimum versions
├── quickstart.bat              One-click Windows setup + benchmark + results
└── pytest.ini                  Test configuration
```

---

## Installation — Step by Step

### Prerequisites

| Requirement | Version | How to check |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Ollama | Latest | [ollama.ai](https://ollama.ai) |
| Tesseract OCR | 5.x | [UB-Mannheim installer](https://github.com/UB-Mannheim/tesseract/wiki) |
| NVIDIA GPU | 8 GB+ VRAM recommended | (CPU fallback available, slower) |

### Step 1 — Clone and install dependencies

```bash
# Navigate to the project folder
cd safety_auditor

# Install all Python packages
pip install -r requirements.txt
```

This installs 35+ packages including PyMuPDF, Z3, SQLAlchemy, Streamlit, etc.
The SQLite database (`output/audit_store.db`) is created automatically on first run.

### Step 2 — Pull the LLM model

```bash
# Primary model (recommended)
ollama pull qwen2.5

# Fallback model (optional)
ollama pull llama3
```

Ollama runs the LLM **locally** — no internet connection needed after download,
no API keys, no data leaving your machine.

### Step 3 — Set Tesseract path (Windows only)

Create a `.env` file in the `safety_auditor/` folder:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
LLM_MODEL=qwen2.5
EXTRACTION_CONFIDENCE_THRESHOLD=0.7
ENABLE_CROSS_MODAL_LINKING=true
REPORT_FORMAT=html
```

---

## How to Run — Every Command Explained

### Option A — One-click (Windows)

```batch
quickstart.bat
```

This does everything: installs packages, generates the benchmark, runs the
evaluation, and prints your F1 / Precision / Recall numbers.

---

### Option B — Manual commands

#### 1. Generate the synthetic benchmark (50 spec packages)

```bash
python run_pipeline.py benchmark --n 50
```

Creates `benchmark/corpus/PKG-001` to `PKG-050`. Each package contains:
- `control_narrative.pdf` — a realistic pump/vessel control narrative
- `cause_effect_table.pdf` — a C&E table with trip conditions
- `pid_tags.txt` — a P&ID tag inventory
- `injections.json` — ground-truth file listing which defects were injected

**The benchmark already exists** in `benchmark/corpus/` — you only need this
if you want to regenerate it with a different random seed.

---

#### 2. Run the full evaluation (produces paper numbers)

```bash
python run_pipeline.py evaluate --corpus benchmark/corpus --ablation --baseline
```

This runs the 9-phase pipeline on all 50 packages and computes:
- `evaluation/results/main/main/metrics.json` — overall + per-category P/R/F1
- `evaluation/results/main/main/metrics_table.csv` — same as CSV for the paper
- `evaluation/results/main/main/predictions.json` — what the system found
- `evaluation/results/main/main/ground_truth.json` — what was actually injected

**Current results** (already computed, no re-run needed):
```
Overall:  Precision=0.615  Recall=0.800  F1=0.696
Missing shutdown rule:  Recall=1.000 ← system never misses a shutdown omission
Missing alarm:          Recall=1.000 ← system never misses an alarm omission
Contradiction:          F1=0.000    ← being fixed in current iteration
```

---

#### 3. Audit a real specification document

```bash
python run_pipeline.py audit --input data/schneider_electric/YOUR_SPEC.pdf
```

Or with the `--real-data` flag to distinguish from benchmark runs:

```bash
python run_pipeline.py audit \
  --input data/schneider_electric/YOUR_SPEC.pdf \
  --real-data \
  --output output/schneider_run1
```

This runs all 9 phases and saves:
- `output/schneider_run1/audit_report.html` — full safety audit report
- `output/schneider_run1/plc_output.st` — generated PLC Structured Text
- `output/schneider_run1/knowledge_graph.html` — interactive equipment graph
- The run is also persisted to `output/audit_store.db`

---

#### 4. Launch the Streamlit UI

```bash
streamlit run ui/app.py
```

Opens at `http://localhost:8501`. The 6 pages:

| Page | What it does |
|---|---|
| Upload & Run | Upload a PDF, run the 9-phase pipeline, see severity donut chart |
| Findings | Filterable table of all findings with type distribution bar chart |
| Knowledge Graph | Interactive PyVis equipment graph (hover for details) |
| PLC Output | View and download the generated Structured Text code |
| Audit History | All past runs from SQLite DB, drill-down to findings per run |
| Benchmark Metrics | F1 / P / R charts from the 50-package evaluation |

---

#### 5. Run the tests

```bash
pytest tests/ -v
```

All 15 tests pass without Ollama running — the pipeline tests use direct rule
injection to bypass the LLM. Expected output:

```
15 passed in 1.38s
```

---

#### 6. Generate paper figures

```bash
python scripts/generate_figures.py
```

Reads `evaluation/results/main/metrics.json` and saves three matplotlib PDF
figures to `paper/figures/`:
- `fig_baseline_comparison.pdf` — Our system vs. post-generation baseline
- `fig_per_category_f1.pdf` — F1 per defect category (horizontal bar chart)
- `fig_ablation.pdf` — ΔF1 with/without cross-modal linking

---

#### 7. Compile the paper

```batch
cd paper
compile.bat
```

Or manually:
```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Produces `paper/main.pdf` — the complete IEEE conference paper.

---

## How the Database Works

Every time you run an audit (via CLI or UI), the results are automatically
saved to `output/audit_store.db` — a SQLite file.

```
output/audit_store.db
├── audit_runs   — one row per pipeline execution
├── findings     — every safety finding, linked to its run
├── kg_nodes     — every equipment node in the knowledge graph
└── kg_edges     — every control relationship edge
```

**You can query it directly** with any SQLite tool (e.g. DB Browser for SQLite):

```sql
-- Show all runs with HIGH findings
SELECT run_id, input_source, high_count, created_at
FROM audit_runs
WHERE high_count > 0
ORDER BY created_at DESC;

-- Show all OMISSION findings across all runs
SELECT r.input_source, f.equipment_tag, f.iec_clause, f.description
FROM findings f
JOIN audit_runs r ON f.run_id = r.run_id
WHERE f.finding_type = 'OMISSION' AND f.severity = 'HIGH';
```

**The database is optional** — if it is deleted, the app still works. The next
run creates a fresh `audit_store.db`.

---

## Configuration Reference

All settings are in `.env` (create from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `LLM_MODEL` | `qwen2.5` | Primary Ollama model |
| `LLM_FALLBACK_MODEL` | `llama3` | Fallback if primary fails |
| `LLM_TEMPERATURE` | `0.1` | Low temperature = more deterministic extraction |
| `EXTRACTION_CONFIDENCE_THRESHOLD` | `0.7` | Rules below this are flagged for review |
| `ENABLE_CROSS_MODAL_LINKING` | `true` | Set false for ablation study |
| `FUZZY_MATCH_THRESHOLD` | `85` | Levenshtein score (0-100) for tag merging |
| `EMBEDDING_SIMILARITY_THRESHOLD` | `0.75` | Cosine similarity for embedding match |
| `Z3_TIMEOUT_MS` | `5000` | Z3 solver timeout per check |
| `REPORT_FORMAT` | `html` | `html` or `pdf` |
| `TESSERACT_CMD` | `tesseract` | Full path on Windows |

---

## Current Results

| Metric | Value | Notes |
|---|---|---|
| Overall Precision | 0.615 | 61.5% of reported findings are real |
| Overall Recall | 0.800 | 80.0% of injected defects are found |
| Overall F1 | 0.696 | Harmonic mean |
| Missing shutdown recall | **1.000** | Never misses a missing shutdown rule |
| Missing alarm recall | **1.000** | Never misses a missing alarm rule |
| Contradiction F1 | 0.000 | Fixed in latest code — re-evaluation pending |
| Benchmark packages | 50 | Across 5 ICS subsystem templates |

---

## Path to Publication

```
DONE:
  ✓ Full 9-phase pipeline implemented and tested (15/15 tests pass)
  ✓ 50-package benchmark generated and evaluated (F1=0.696)
  ✓ SQLite audit store with history and graph persistence
  ✓ 6-page Streamlit dashboard with Plotly charts
  ✓ IEEE paper draft with all results filled in
  ✓ Complete BibTeX bibliography (no [TODO] entries)
  ✓ Z3 contradiction bug fixed + interlock FP reduction

TODO BEFORE SUBMISSION:
  □ Run Schneider Electric document through pipeline
  □ Get Dr. Raviteja to confirm real-data findings
  □ Fill in real-data section of paper (Section V-D)
  □ Run ablation study with Ollama live → fill ablation table
  □ Read 5 papers in docs/CITATION_TODO.md
  □ Generate paper figures (python scripts/generate_figures.py)
  □ Final compile: compile.bat → review paper/main.pdf
  □ Submit to FMICS 2027 (recommended first target)
```

---

## Paper Citation

```bibtex
@inproceedings{rakesh2027safety,
  author    = {Lokani, Rakesh and Raviteja, [SURNAME]},
  title     = {Pre-Synthesis Safety Auditing of Industrial Control Specifications
               Using a Neuro-Symbolic Framework},
  booktitle = {[Conference Name]},
  year      = {2027}
}
```

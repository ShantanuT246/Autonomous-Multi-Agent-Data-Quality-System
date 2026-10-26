# Autonomous Data Cleaning Agent: End-to-End Roadmap

**Stack:** Python · NumPy · Pandas · Scikit-learn · Matplotlib · Gemini API · LangGraph · MongoDB · FastAPI · React
**Timeline:** ~8 weeks
**Status:** Member 1 (`data_processing` module) is DONE. Member 2 (backend / agents) is starting now. Member 3 (React frontend) comes later.

---

## 0. The Big Picture

```
Upload (CSV/Excel)
      │
      ▼
 Profiler ──► Detector ──► Planner ──► Cleaner ──► Validator
                              ▲                        │
                              │     issues remain      │
                              └────────────────────────┤
                                                       │ valid / max iterations
                                                       ▼
                                                 Report Agent
                                                       │
                                                       ▼
                                   Clean Dataset + Explainable Quality Report
```

**Core design principle:** the LLM *decides*, deterministic Python *executes*.
Gemini never edits data directly. It outputs structured JSON plans (validated with Pydantic), and your Pandas/Scikit-learn tools carry them out. This keeps the system safe, testable, reproducible, and explainable.

---

## 1. What Member 1 Already Gives You (and What's Missing)

| Already built (`data_processing/`) | Gap you must fill in the backend |
|---|---|
| `profile_dataset(df)`: rows, cols, dtypes, missing, duplicates, unique, stats, non-finite | No detection of invalid values (`-5`, `150`), inconsistent categories (`M`/`male`), wrong dtypes, unit issues, outliers |
| `clean_dataset(df)`: median / mode imputation, whitespace and case normalization, cleaning log | Fixed strategy only; no duplicate removal, no outlier handling, no per-column decisions, no category mapping |
| `generate_quality_report(...)`: before/after missing and duplicate charts | No quality score, no narrative report, only 2 charts |
| `run_pipeline(df, output_dir)` | Linear, not agentic; no feedback loop |

**Action:** treat Member 1's module as your **toolbox**. Wrap its functions as LangGraph tools and extend them with new operations (see Phase 2).

---

## Phase 0: Setup and Decisions (Days 1-3)

- [ ] Create the repo structure:
  ```
  project/
  ├── data_processing/        # Member 1 (done)
  ├── backend/
  │   ├── app/
  │   │   ├── main.py             # FastAPI entry
  │   │   ├── config.py           # env vars, settings
  │   │   ├── api/                # routes
  │   │   ├── agents/             # one file per agent
  │   │   ├── graph/              # LangGraph state + workflow
  │   │   ├── tools/              # deterministic cleaning tools
  │   │   ├── llm/                # Gemini client + prompts
  │   │   ├── db/                 # MongoDB layer
  │   │   ├── schemas/            # Pydantic models
  │   │   └── reports/            # report builders
  │   └── tests/
  ├── frontend/               # Member 3 (later)
  ├── sample_data/            # messy test datasets
  ├── .env.example
  └── README.md
  ```
- [ ] Create `.env` with `GEMINI_API_KEY`, `MONGODB_URI`, `OUTPUT_DIR`. Add `.env` to `.gitignore`.
- [ ] Install: `fastapi uvicorn pydantic python-multipart openpyxl pymongo motor langgraph langchain-google-genai google-genai python-dotenv`
- [ ] Set up MongoDB (local install, Docker, or Atlas free tier).
- [ ] Verify your Gemini API key with a "hello world" call. Check the current model names in Google's docs and put the chosen model in `config.py`.
- [ ] **Agree on the API contract with Member 3 now** (endpoints + JSON shapes, see Phase 8). This lets frontend work start without waiting on you.
- [ ] Build **3-5 messy test datasets** with deliberately injected problems (see Phase 1.5). You'll use them for the entire project.

**Milestone:** the repo runs, Gemini responds, MongoDB connects, test datasets exist.

---

## Phase 1: Foundations (Week 1)

### 1.1 Define the shared state (the "dataset state" all agents work on)

Create a Pydantic/TypedDict `CleaningState` for LangGraph:

```python
class CleaningState(TypedDict):
    run_id: str
    original_df_ref: str          # pointer to stored original (don't pass big DataFrames around)
    current_df_ref: str           # pointer to the latest working copy
    initial_profile: dict
    current_profile: dict
    detected_issues: list[Issue]
    cleaning_plan: list[PlannedAction]
    execution_log: list[LogEntry]
    validation_result: ValidationResult
    iteration: int
    max_iterations: int           # e.g. 3
    failed_strategies: list[dict] # so the Planner doesn't repeat mistakes
    initial_score: float
    final_score: float
    status: str
    report: dict
```

> Store DataFrames on disk (Parquet/CSV) or GridFS and keep only references in state. Don't serialize big DataFrames into the LangGraph state or MongoDB documents (16 MB document limit).

### 1.2 Define the schemas (Pydantic)

- [ ] `Issue`: `{id, column, issue_type, severity, description, affected_count, examples[]}`
- [ ] `PlannedAction`: `{id, issue_id, column, action, params, rationale, risk_level}`
- [ ] `LogEntry`: `{column, issue, action, records_changed, before_sample, after_sample, timestamp, status}`
- [ ] `ValidationResult`: `{passed: bool, remaining_issues[], regressions[], integrity_checks{}, score}`
- [ ] Enums for `issue_type` and `action`, a **closed vocabulary** so Gemini can't invent operations.

**Issue types:** `missing_values`, `duplicate_rows`, `invalid_value`, `outlier`, `inconsistent_category`, `wrong_dtype`, `invalid_format`, `contradictory_value`, `unit_inconsistency`

**Allowed actions:** `impute_median`, `impute_mean`, `impute_mode`, `impute_constant`, `fill_unknown`, `drop_duplicates`, `standardize_categories`, `cast_dtype`, `parse_dates`, `clip_outliers`, `set_null_invalid`, `drop_rows`, `strip_whitespace`, `normalize_case`, `convert_units`, `flag_for_review`, `no_action`

### 1.3 Build the Gemini wrapper (`llm/client.py`)

- [ ] Single function: `call_llm(prompt, response_schema) -> validated Pydantic object`
- [ ] Use structured/JSON output mode with your Pydantic schema.
- [ ] Add retry with backoff (rate limits), timeout, and a **JSON-repair/re-ask fallback** if validation fails.
- [ ] Log every prompt/response pair to MongoDB (great for debugging and for the report's "agent reasoning" section).
- [ ] Temperature low (0-0.2) for planning/detection.

### 1.4 Build the MongoDB layer (`db/`)

Collections:

| Collection | Stores |
|---|---|
| `datasets` | metadata: filename, upload time, shape, file path / GridFS id |
| `runs` | run_id, status, timestamps, iteration count, scores |
| `agent_states` | state snapshot per node/iteration (enables replay and the UI timeline) |
| `cleaning_logs` | transformation log entries |
| `llm_calls` | prompts, responses, latency, tokens |
| `reports` | final report JSON + file paths |

- [ ] Use **GridFS** (or disk + path) for actual dataset files.
- [ ] Write CRUD helpers and index on `run_id`.

### 1.5 Create messy test datasets

Inject known problems so you can measure whether the system finds and fixes them:

- Missing values (numeric + categorical, varying percentages)
- Exact duplicate rows (and near-duplicates)
- Age = `-5`, `150`, `999`
- Gender = `Male`, `M`, `male`, `MALE `, `m`, `F`, `female`
- Numbers stored as strings (`"1,200"`, `"$45"`, `"N/A"`)
- Mixed date formats (`2024-01-05`, `05/01/2024`, `Jan 5 2024`)
- Unit inconsistencies (height in cm and in feet, weight in kg and lbs)
- Contradictions (`end_date < start_date`, `age=5` but `marital_status=Married`)
- Outliers (salary = 10,000,000 among ~50,000)
- Keep a **ground-truth clean version** of each, so you can compute accuracy of the cleaning.

**Milestone:** schemas, state, Gemini wrapper, DB layer, and test data all ready.

---

## Phase 2: Deterministic Tool Layer (Weeks 1-2)

This is the "hands" of the system. Every tool is a plain Python function: `(df, **params) -> (new_df, LogEntry)`. **No LLM inside tools.**

### 2.1 Wrap Member 1's code
- [ ] `tools/profile.py` wraps `profile_dataset`
- [ ] `tools/impute.py` wraps median / mode imputation from `clean_dataset`
- [ ] `tools/text.py` wraps whitespace and capitalization normalization
- [ ] Refactor so each operation can be called **per column, individually** (Member 1's `clean_dataset` runs everything at once; agents need fine-grained control).

### 2.2 Add the missing tools

| Tool | What it does |
|---|---|
| `drop_duplicates` | Removes exact duplicates (optionally on a subset), logs the count |
| `standardize_categories(col, mapping)` | Applies a value mapping (`M → Male`) |
| `cast_dtype(col, dtype)` | Safe type conversion; strips `$`, `,`, handles `"N/A"` |
| `parse_dates(col, formats)` | Normalizes mixed date formats to ISO |
| `set_null_invalid(col, rule)` | Replaces impossible values (`age < 0 or > 120`) with NaN so they can be imputed |
| `clip_outliers(col, method)` | IQR / z-score winsorizing |
| `convert_units(col, factor, condition)` | Handles unit inconsistencies |
| `impute_knn` / `impute_mean` / `impute_constant` | Extra imputation options (Scikit-learn `KNNImputer`, `SimpleImputer`) |
| `flag_for_review` | Doesn't change data, records an item for the "recommended manual checks" section |

### 2.3 Add the detection helpers (statistical, no LLM)
- [ ] **Outliers:** IQR and z-score / modified z-score (NumPy)
- [ ] **Category inconsistency:** normalize (lower/strip) then group; also fuzzy matching (`difflib` or `rapidfuzz`) to cluster near-identical labels
- [ ] **Dtype inference:** columns of dtype `object` where > ~90% of values parse as numbers/dates
- [ ] **Format validation:** regex checks for emails, phones, zip codes
- [ ] **Range sanity:** min/max compared to column-name hints (`age`, `price`, `percentage`)
- [ ] **Cross-column rules:** date ordering, etc. (let the LLM *propose* rules, then execute them in code)

### 2.4 Tool registry and safety
- [ ] A registry dict `{action_name: function}` that the Cleaner uses to dispatch.
- [ ] **Every tool operates on a copy**, never mutates the original.
- [ ] Row-loss guard: if an action would delete > X% of rows (say 20%), block it and escalate to the Planner or `flag_for_review`.
- [ ] Unit-test every tool on small hand-made DataFrames.

**Milestone:** you can clean a dataset manually by calling tools, with a full log. No LLM needed yet.

---

## Phase 3: Quality Score (Week 2)

You need a number for "initial vs. final data-quality score."

- [ ] Define a **0-100 score** from weighted components:

  | Component | Example weight |
  |---|---|
  | Completeness (1 − missing ratio) | 25% |
  | Uniqueness (1 − duplicate ratio) | 15% |
  | Validity (values within valid ranges/formats) | 25% |
  | Consistency (categories, units, formats) | 20% |
  | Type correctness | 10% |
  | Outlier ratio | 5% |

- [ ] Implement `compute_quality_score(df, issues) -> {total, components}`.
- [ ] Test: score on a messy dataset is low, on its ground-truth clean version is ~100.
- [ ] Document the formula (it will appear in the report and your project write-up).

---

## Phase 4: The Agents (Weeks 3-4)

Each agent = a LangGraph **node** (a function taking state, returning a state update). Build and test each **independently** before wiring them together.

### 4.1 Dataset Profiler Agent
- **Input:** raw DataFrame
- **Does:** calls Member 1's `profile_dataset` + extra profiling (categorical distributions, numeric ranges, top-N values, sample rows)
- **Output:** `initial_profile`, `initial_score`
- **LLM use:** optional, a short natural-language dataset summary ("looks like HR employee data") that gives downstream agents context
- Re-runs after each cleaning pass to refresh `current_profile`

### 4.2 Data Quality Detection Agent
- **Input:** profile + samples + statistical-detector output (Phase 2.3)
- **Hybrid approach:**
  1. Run statistical detectors → candidate issues (cheap, reliable)
  2. Send a **compact** profile (not the whole dataset) to Gemini to find semantic problems the stats can't: impossible values, contradictions, unit problems, suspicious columns
- **Output:** `list[Issue]` (structured, deduplicated, severity-ranked)
- **Prompt tips:** include column names, dtypes, min/max, top values, 10-20 sample rows; instruct it to return only issue types from your enum; demand evidence (examples) per issue.

### 4.3 Cleaning Planner Agent
- **Input:** issues + profile + `failed_strategies` (from earlier iterations)
- **Output:** `list[PlannedAction]`, one decision per issue with rationale
- **Reasoning rules to encode in the prompt:**
  - Consider column type, distribution (skewed → median, not mean), % missing (if > ~60% missing, suggest drop column or flag), and semantic context
  - Extreme values → `flag_for_review` or clip, not blind deletion
  - Never drop > threshold of rows
  - Categorical mapping: Gemini proposes the mapping dict (`{"M":"Male","male":"Male"}`); you validate that keys exist in the data
  - Order matters: **fix dtypes → fix invalid values → standardize categories → dedupe → impute → handle outliers**
- **Post-process in code:** validate actions against the allowed enum and column existence; sort by the canonical order; reject malformed actions.
- **Optional human-in-the-loop:** the plan can be surfaced to the UI for approval ("approved transformations" in the project text). LangGraph supports interrupts/checkpoints for this.

### 4.4 Data Cleaning Agent (Executor)
- **Mostly deterministic**: loops over the plan, dispatches to the tool registry, collects `LogEntry`s
- Wraps each action in try/except; a failed action is logged as `failed`, not fatal
- Saves the cleaned DataFrame snapshot per iteration (enables rollback)
- **Log format** (matches the spec):
  ```
  Column: Gender
  Issue: Inconsistent categories
  Action: Standardization
  Changed: 37 records
  ```

### 4.5 Validation Agent
- **Input:** original df, cleaned df, plan, log
- **Deterministic checks:**
  - Missing values reduced? Duplicates gone? Dtypes correct?
  - Re-run the detectors on the cleaned data → remaining issues
  - **Integrity checks:** row count change within tolerance, no unexpected new NaNs, column set unchanged (unless intended), numeric distribution not wildly distorted (mean/std before vs. after, KS-test optional), no regressions
- **LLM use (optional):** review the remaining issues and judge whether they're acceptable or need re-planning
- **Output:** `ValidationResult` + `final_score`
- Decides routing: `passed` / `needs_replan`

### 4.6 Report Agent
- **Input:** everything: scores, issues, log, validation, charts
- **Output:** the full report (see Phase 6)
- **LLM use:** write the narrative sections (executive summary, explanation of decisions, recommended manual checks), grounded **only** in the log and metrics you pass in, to prevent hallucination

**Milestone:** each agent works standalone on your test datasets with printed output.

---

## Phase 5: LangGraph Orchestration and Self-Correction Loop (Week 5)

### 5.1 Build the graph

```python
graph = StateGraph(CleaningState)
graph.add_node("profiler", profiler_node)
graph.add_node("detector", detector_node)
graph.add_node("planner",  planner_node)
graph.add_node("cleaner",  cleaner_node)
graph.add_node("validator", validator_node)
graph.add_node("reporter", reporter_node)

graph.set_entry_point("profiler")
graph.add_edge("profiler", "detector")
graph.add_edge("detector", "planner")
graph.add_edge("planner",  "cleaner")
graph.add_edge("cleaner",  "validator")
graph.add_conditional_edges("validator", route_after_validation, {
    "replan": "planner",
    "done":   "reporter",
})
graph.add_edge("reporter", END)
```

### 5.2 The routing function
```python
def route_after_validation(state):
    if state["validation_result"].passed:           return "done"
    if state["iteration"] >= state["max_iterations"]: return "done"   # give up gracefully
    return "replan"
```

### 5.3 Self-correction details (the most "agentic" part)
- [ ] On `replan`, pass the Planner: remaining issues + what was tried + what failed/regressed (`failed_strategies`) so it picks an **alternative strategy** (e.g., median → KNN imputation; clip → flag).
- [ ] **Rollback:** if an iteration made things worse (score dropped), revert to the best snapshot so far.
- [ ] **Termination guarantees:** hard `max_iterations` (2-3), and stop early if the score stops improving.
- [ ] Anything unresolved at the end goes into "Remaining issues / manual checks."

### 5.4 Persistence and observability
- [ ] Use a LangGraph checkpointer (MongoDB-backed or in-memory first) so runs are resumable.
- [ ] Save a state snapshot to `agent_states` after every node.
- [ ] Emit progress events (`"profiling"`, `"detecting"`, `"planning"`, `"cleaning iteration 2"`, ...) so the frontend can show live progress.
- [ ] Add LangSmith tracing (optional) or your own trace logs.

**Milestone:** upload → run graph → get a cleaned dataset and log from a single function call `run_cleaning_graph(df)`.

---

## Phase 6: Reporting and Visualization (Week 6)

### 6.1 Report content (per the spec)
1. Dataset overview (rows/cols, types)
2. **Initial quality score** (with component breakdown)
3. **Detected problems** (table: column, issue, severity, count)
4. **Cleaning decisions** with the Planner's rationale
5. **Operations performed** (the transformation log)
6. **Number of affected records** per operation and in total
7. **Final quality score** (with the improvement delta)
8. **Remaining issues**
9. **Recommended manual checks**
10. Iteration history (what was re-planned and why)

### 6.2 Visualizations (extend Member 1's `visualizer.py`)
- [ ] Missing values before vs. after (already exists)
- [ ] Duplicates before vs. after (already exists)
- [ ] Quality score gauge or bar (initial vs. final) and component radar/bar
- [ ] Distribution histograms before vs. after for key numeric columns
- [ ] Outlier box plots before vs. after
- [ ] Category frequency before vs. after (e.g., Gender)
- [ ] Records changed per column (bar)
- [ ] Score per iteration line chart

### 6.3 Output formats
- [ ] **JSON** (for the React UI, primary)
- [ ] **Markdown or HTML** (human-readable; embed charts as base64 or relative paths)
- [ ] Optional **PDF** export (WeasyPrint or ReportLab)
- [ ] Cleaned dataset download (CSV + Excel) and the transformation log as CSV/JSON

**Milestone:** a complete, readable before/after report generated from a run.

---

## Phase 7: API Layer (Week 6-7)

FastAPI serves as the bridge to the React frontend.

### 7.1 Endpoints (agree these with Member 3 early)

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/datasets/upload` | Upload CSV/Excel → returns `dataset_id`, preview, basic shape |
| `POST` | `/api/runs` | Start a cleaning run for a `dataset_id` → returns `run_id` (run in background) |
| `GET`  | `/api/runs/{run_id}` | Status, current stage, iteration, scores |
| `GET`  | `/api/runs/{run_id}/stream` | SSE or WebSocket for live progress events |
| `GET`  | `/api/runs/{run_id}/issues` | Detected issues |
| `GET`  | `/api/runs/{run_id}/plan` | Cleaning plan (+ rationale) |
| `POST` | `/api/runs/{run_id}/plan/approve` | *(optional)* human approval / edit of plan |
| `GET`  | `/api/runs/{run_id}/log` | Transformation log |
| `GET`  | `/api/runs/{run_id}/report` | Report JSON |
| `GET`  | `/api/runs/{run_id}/charts/{name}` | Chart images |
| `GET`  | `/api/runs/{run_id}/download?format=csv` | Cleaned dataset |
| `GET`  | `/api/runs` | History of past runs |

### 7.2 Engineering details
- [ ] Run the graph in a **background task** (FastAPI `BackgroundTasks`, or Celery/RQ if it gets heavy). Never block the request.
- [ ] Validate uploads: allowed extensions, size limit (e.g., 50 MB), encoding detection (`chardet`/`charset-normalizer`), Excel sheet selection.
- [ ] CORS enabled for the React dev server.
- [ ] Consistent error format (`{error, detail}`) and proper status codes.
- [ ] Auto-generated docs at `/docs` (give the link to Member 3).

**Milestone:** you can run the full flow with only `curl` / Swagger UI.

---

## Phase 8: Frontend Handoff (Week 7, Member 3)

Even though you said frontend comes later, prepare these for Member 3:

- [ ] Stable API contract + example JSON responses (put them in `/docs/api_examples/`).
- [ ] Seed data / a mock mode so the UI can be developed without Gemini calls.
- [ ] **UI screens to build:**
  1. Upload page (drag-and-drop + data preview table)
  2. Live pipeline view (agent stages with progress, as in the architecture diagram)
  3. Detected issues table
  4. Cleaning plan view (approve/edit, optional)
  5. Transformation log viewer
  6. Before vs. after dashboard (scores, charts, side-by-side table)
  7. Final report page + download buttons (CSV, report, log)
  8. Run history
- [ ] Suggested libs: React + Vite, TanStack Query, Recharts (or display the Matplotlib PNGs), Tailwind or MUI, `react-dropzone`.

---

## Phase 9: Testing and Evaluation (Weeks 7-8)

### 9.1 Automated tests
- [ ] **Unit:** every tool, detector, score function, schema validator
- [ ] **Agent tests with a mocked LLM:** feed canned Gemini responses, assert state updates (fast, free, deterministic)
- [ ] **Graph tests:** the loop terminates, replans on failure, respects `max_iterations`
- [ ] **API tests:** FastAPI `TestClient` for each endpoint
- [ ] **Failure tests:** empty file, single-column file, all-null column, huge cardinality column, non-UTF8 file, malformed JSON from Gemini, Gemini timeout

### 9.2 Evaluation (this makes your project defensible)
- [ ] Use the datasets with known ground truth and report:
  - Issue **detection precision/recall** (did it find the injected problems?)
  - **Cleaning accuracy** (% of cells matching ground truth after cleaning)
  - Quality score improvement
  - Number of iterations needed
  - Runtime and number of LLM calls/tokens per run
- [ ] **Baseline comparison:** compare against Member 1's fixed-rule `run_pipeline`. Show where the agentic approach wins (e.g., handles `-5`/`150`, category mapping, dtype fixes, unit conversions).
- [ ] Test on 2-3 **real public datasets** (Kaggle: Titanic, Adult Census, a messy HR/sales dataset) to prove generalization to "unfamiliar datasets."

### 9.3 Hardening
- [ ] Prompt-injection safety: dataset cell contents are **data, not instructions**. Wrap them in delimiters and tell Gemini to ignore any instructions found inside.
- [ ] Don't send full datasets to Gemini: only profiles and small samples (cost, privacy, token limits). Mention this in the privacy notes.
- [ ] Cap LLM calls per run; cache identical prompts.
- [ ] Reproducibility: fixed random seeds; store the plan JSON so a run can be replayed without the LLM.

---

## Phase 10: Documentation, Packaging and Demo (Week 8)

- [ ] Root `README.md`: architecture diagram, setup, env vars, how to run backend + frontend, example screenshots
- [ ] Update `data_processing/README.md` limitations (duplicate removal and outlier handling are now covered by the agent tools)
- [ ] `docker-compose.yml`: backend + MongoDB + frontend
- [ ] `requirements.txt` / `pyproject.toml` pinned versions
- [ ] Architecture + sequence diagrams for the project report/presentation
- [ ] **Demo script:** pick a messy dataset → upload → watch agents → show the self-correction loop in action → show the report. Prepare a backup recorded video in case the live Gemini API fails.
- [ ] Final report/presentation: problem, methodology, architecture, results (evaluation tables from 9.2), limitations, future work

---

## 8-Week Timeline Summary

| Week | Focus | Deliverable |
|---|---|---|
| **1** | Setup, schemas, state, Gemini wrapper, MongoDB, test data, start tools | Foundations ready |
| **2** | Tool layer complete, detectors, quality score | Manual cleaning works with logs and score |
| **3** | Profiler + Detector agents | Issues detected on all test sets |
| **4** | Planner + Cleaner + Validator + Report agents (standalone) | Each agent verified independently |
| **5** | LangGraph wiring, self-correction loop, rollback, checkpoints | End-to-end graph run |
| **6** | Reports and visualizations, FastAPI endpoints | Full report + working API |
| **7** | Frontend integration with Member 3, SSE progress, testing | Working UI + tests |
| **8** | Evaluation, hardening, docs, Docker, demo | Final submission |

> If you fall behind, cut in this order: PDF export → plan-approval UI → WebSocket streaming (use polling) → KNN imputation / unit conversion. **Never cut:** the self-correction loop, the transformation log, the quality score, or the before/after report. Those define the project.

---

## Key Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Gemini returns malformed JSON | Structured output + Pydantic validation + retry/re-ask |
| LLM proposes destructive actions | Closed action enum, row-loss guard, rollback, `flag_for_review` |
| Hallucinated column names / mappings | Validate every plan item against the real DataFrame before executing |
| Infinite replanning loop | `max_iterations` + no-improvement early stop |
| Large datasets blow the token limit | Send only compact profiles + samples, never the full data |
| API rate limits / downtime | Backoff, caching, mock-LLM mode, replayable stored plans |
| Mongo 16 MB document limit | GridFS / files on disk, with references in documents |
| Sensitive data sent to a third-party LLM | Send aggregates and a few masked samples; document this |

---

## Immediate Next Steps (Do This Week)

1. Set up the repo structure, `.env`, and MongoDB, and make a first Gemini call.
2. Write the Pydantic schemas and `CleaningState`.
3. Create 3 messy datasets and their ground-truth clean versions.
4. Wrap Member 1's `profile_dataset` / `clean_dataset` as individual tools.
5. Build the quality-score function.
6. Message Member 3 with the draft API contract from Phase 7.

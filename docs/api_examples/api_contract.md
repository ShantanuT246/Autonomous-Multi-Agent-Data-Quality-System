# API Contract & Specifications for Member 3 (Frontend)

Base URL: `http://localhost:8000/api`

## Endpoints Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/datasets/upload` | Upload CSV or Excel file. Returns metadata and sample preview. |
| `GET` | `/datasets/{dataset_id}` | Retrieve uploaded dataset details and preview rows. |
| `POST` | `/runs` | Start an autonomous cleaning run (runs in background). |
| `GET` | `/runs` | List past cleaning runs. |
| `GET` | `/runs/{run_id}` | Get run status, current stage, iteration, scores. |
| `GET` | `/runs/{run_id}/stream` | SSE stream for real-time progress events. |
| `GET` | `/runs/{run_id}/issues` | List of all detected data quality issues. |
| `GET` | `/runs/{run_id}/plan` | Cleaning plan (planned actions + rationales). |
| `POST`| `/runs/{run_id}/plan/approve` | (Optional) Approve or modify plan before execution. |
| `GET` | `/runs/{run_id}/log` | Complete transformation log of all operations performed. |
| `GET` | `/runs/{run_id}/report` | Final comprehensive JSON report (scores, delta, narrative). |
| `GET` | `/runs/{run_id}/charts/{chart_name}` | Quality report chart images (.png). |
| `GET` | `/runs/{run_id}/download` | Download cleaned dataset (`format=csv` or `format=xlsx`). |

---

## Example Payloads & Responses

### 1. `POST /api/datasets/upload`
**Request:** `multipart/form-data` with `file: File`
**Response (200 OK):**
```json
{
  "dataset_id": "ds_671bb5d2e4",
  "filename": "customers_messy.csv",
  "file_size_bytes": 1024,
  "rows": 11,
  "columns": 7,
  "column_names": ["customer_id", "name", "age", "gender", "signup_date", "annual_spend", "loyalty_score"],
  "preview": [
    {
      "customer_id": 101,
      "name": "Alice Smith ",
      "age": 28,
      "gender": "Female",
      "signup_date": "2023-01-15",
      "annual_spend": "$1,250.50",
      "loyalty_score": 85
    }
  ]
}
```

### 2. `POST /api/runs`
**Request:**
```json
{
  "dataset_id": "ds_671bb5d2e4",
  "max_iterations": 3,
  "require_plan_approval": false
}
```
**Response (202 Accepted):**
```json
{
  "run_id": "run_982fa10",
  "dataset_id": "ds_671bb5d2e4",
  "status": "queued",
  "message": "Autonomous cleaning pipeline queued in background."
}
```

### 3. `GET /api/runs/{run_id}`
**Response (200 OK):**
```json
{
  "run_id": "run_982fa10",
  "dataset_id": "ds_671bb5d2e4",
  "status": "completed",
  "current_stage": "done",
  "iteration": 1,
  "max_iterations": 3,
  "initial_score": 64.5,
  "final_score": 98.0,
  "score_improvement": 33.5,
  "created_at": "2026-10-26T21:55:00Z",
  "completed_at": "2026-10-26T21:55:12Z"
}
```

### 4. `GET /api/runs/{run_id}/stream` (SSE Event Stream)
```
event: progress
data: {"stage": "profiling", "iteration": 0, "message": "Profiling initial dataset..."}

event: progress
data: {"stage": "detecting", "iteration": 0, "message": "Statistical and LLM quality detection running..."}

event: progress
data: {"stage": "planning", "iteration": 1, "message": "Planning cleaning actions and reasoning..."}

event: progress
data: {"stage": "cleaning", "iteration": 1, "message": "Executing deterministic transformations..."}

event: progress
data: {"stage": "validating", "iteration": 1, "message": "Verifying data integrity and quality score..."}

event: progress
data: {"stage": "reporting", "iteration": 1, "message": "Generating quality charts and narrative report..."}

event: complete
data: {"status": "completed", "final_score": 98.0}
```

### 5. `GET /api/runs/{run_id}/issues`
**Response (200 OK):**
```json
[
  {
    "id": "ISSUE-1",
    "column": "annual_spend",
    "issue_type": "wrong_dtype",
    "severity": "high",
    "description": "Numeric column stored as formatted currency strings with symbols '$' and commas.",
    "affected_count": 3,
    "examples": ["$1,250.50", "$4,500.00", "$5,100"]
  },
  {
    "id": "ISSUE-2",
    "column": "gender",
    "issue_type": "inconsistent_category",
    "severity": "medium",
    "description": "Inconsistent casing and abbreviation codes for gender values.",
    "affected_count": 5,
    "examples": ["M", "male", "F", "female", "MALE "]
  }
]
```

### 6. `GET /api/runs/{run_id}/log`
**Response (200 OK):**
```json
[
  {
    "column": "annual_spend",
    "issue": "wrong_dtype",
    "action": "cast_dtype",
    "records_changed": 10,
    "before_sample": "$1,250.50",
    "after_sample": "1250.5",
    "timestamp": "2026-10-26T21:55:04Z",
    "status": "success"
  },
  {
    "column": "gender",
    "issue": "inconsistent_category",
    "action": "standardize_categories",
    "records_changed": 5,
    "before_sample": "M",
    "after_sample": "Male",
    "timestamp": "2026-10-26T21:55:05Z",
    "status": "success"
  }
]
```

### 7. `GET /api/runs/{run_id}/report`
**Response (200 OK):**
```json
{
  "run_id": "run_982fa10",
  "dataset_overview": {
    "rows": 10,
    "columns": 7,
    "total_cells": 70
  },
  "initial_score": {
    "total": 64.5,
    "components": {
      "completeness": 85.0,
      "uniqueness": 90.0,
      "validity": 55.0,
      "consistency": 40.0,
      "type_correctness": 60.0,
      "outlier_ratio": 95.0
    }
  },
  "final_score": {
    "total": 98.0,
    "components": {
      "completeness": 100.0,
      "uniqueness": 100.0,
      "validity": 96.0,
      "consistency": 98.0,
      "type_correctness": 100.0,
      "outlier_ratio": 98.0
    }
  },
  "score_improvement": 33.5,
  "executive_summary": "Cleaned dataset with 10 records. Standardized 5 inconsistent gender entries, removed 1 duplicate record, converted currency formatted strings to float, and imputed missing numeric values with median.",
  "operations_summary": {
    "total_operations": 5,
    "total_records_affected": 18
  },
  "remaining_issues": [],
  "recommended_manual_checks": [
    "Verify whether loyalty_score imputation matches company business tiering rules."
  ],
  "charts": {
    "missing_values": "/api/runs/run_982fa10/charts/missing_values",
    "duplicate_rows": "/api/runs/run_982fa10/charts/duplicate_rows",
    "quality_score_comparison": "/api/runs/run_982fa10/charts/quality_score_comparison",
    "records_changed": "/api/runs/run_982fa10/charts/records_changed"
  }
}
```

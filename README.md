# Autonomous Multi-Agent Data Quality System

An autonomous, agentic data quality and cleaning system that combines LLM reasoning (Google Gemini) with deterministic Python execution (Pandas, Scikit-learn, LangGraph, MongoDB, FastAPI, React).

## Core Design Principle
**The LLM decides, deterministic Python executes.**  
Gemini never edits data directly. It outputs structured JSON plans validated with Pydantic, and verified Pandas/Scikit-learn tools execute them safely with integrity checks, rollback protection, and full audit logs.

## Architecture

```
Upload (CSV / Excel)
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

## Tech Stack
- **Python 3.9+**
- **LangGraph** (StateGraph multi-agent workflow & self-correction loop)
- **Google Gemini API** (`langchain-google-genai` / `google-genai`)
- **Pandas & NumPy** (Data manipulation)
- **Scikit-learn** (Statistical imputers and transforms)
- **Matplotlib** (Quality reporting and visualization)
- **FastAPI & Uvicorn** (RESTful API & SSE progress streams)
- **MongoDB & Motor** (Dataset metadata, agent run checkpoints, audit logs)
- **React** (Frontend UI)

## Repository Structure
```
├── data_processing/        # Core profiling and baseline processing
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI application entry point
│   │   ├── config.py       # Pydantic environment settings
│   │   ├── api/            # API routes and endpoints
│   │   ├── agents/         # LangGraph node agents (profiler, detector, planner, cleaner, validator, reporter)
│   │   ├── graph/          # Workflow state and graph definition
│   │   ├── tools/          # Deterministic data cleaning and detection tools
│   │   ├── llm/            # Gemini client wrapper, prompts, structured output
│   │   ├── db/             # MongoDB async & sync client, GridFS storage
│   │   ├── schemas/        # Pydantic models & enums
│   │   └── reports/        # Report and visualization generators
│   └── tests/              # Backend unit and integration tests
├── sample_data/            # Messy test datasets & ground-truth clean pairs
├── frontend/               # React client
├── .env.example            # Example configuration
└── README.md
```

## Quick Start

1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Configure `.env`:
   ```bash
   cp .env.example .env
   # Add your GEMINI_API_KEY
   ```
3. Start MongoDB:
   ```bash
   brew services start mongodb-community
   ```
4. Run FastAPI development server:
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```

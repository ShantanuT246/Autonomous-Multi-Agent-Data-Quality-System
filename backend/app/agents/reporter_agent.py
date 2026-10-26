import json
import logging
from pathlib import Path
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from backend.app.config import settings
from backend.app.db.repository import repo
from backend.app.graph.state import CleaningState, load_dataframe_ref
from backend.app.llm.client import call_llm
from backend.app.reports.quality_score import compute_quality_score
from backend.app.reports.visualizer import generate_pipeline_charts
from backend.app.schemas.enums import RunStatus

logger = logging.getLogger(__name__)


class NarrativeReport(BaseModel):
    executive_summary: str = Field(default="Dataset cleaned and validated successfully.", description="High-level summary of the cleaning results and impact")
    decisions_explanation: str = Field(default="Applied automated standardization, type casting, and statistical imputation.", description="Clear explanation of why key transformations were chosen")
    recommended_manual_checks: List[str] = Field(default_factory=list, description="Follow-up recommendations for data stewards")


def reporter_node(state: CleaningState) -> Dict[str, Any]:
    """
    Report Agent:
    - Generates visual comparison charts (PNG).
    - Writes grounded narrative sections via Gemini.
    - Saves the final cleaned dataset as CSV and Excel.
    - Persists the complete report into MongoDB.
    """
    run_id = state.get("run_id", "default_run")
    original_ref = state.get("original_df_ref")
    final_ref = state.get("best_df_ref") or state.get("current_df_ref")

    df_original = load_dataframe_ref(original_ref)
    df_cleaned = load_dataframe_ref(final_ref)

    initial_score = float(state.get("initial_score", 0.0))
    final_score_obj = compute_quality_score(df_cleaned)
    final_score = float(final_score_obj.total)
    score_delta = round(final_score - initial_score, 2)

    logs = state.get("execution_log", [])
    validation = state.get("validation_result", {})
    remaining_issues = validation.get("remaining_issues", [])

    # 1. Generate before/after charts
    chart_paths = generate_pipeline_charts(
        original_df=df_original,
        cleaned_df=df_cleaned,
        initial_score=initial_score,
        final_score=final_score,
        logs=logs,
        run_id=run_id,
    )

    # 2. Save cleaned dataset in user-facing formats (CSV & Excel)
    run_output_dir = settings.OUTPUT_DIR / run_id
    run_output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = run_output_dir / "cleaned_dataset.csv"
    xlsx_path = run_output_dir / "cleaned_dataset.xlsx"

    df_cleaned.to_csv(csv_path, index=False)
    try:
        df_cleaned.to_excel(xlsx_path, index=False)
    except Exception as e:
        logger.warning(f"Could not save Excel export: {e}")

    # 3. LLM narrative generation (grounded strictly in facts/metrics)
    prompt = f"""
Write an executive summary, decisions explanation, and recommended manual checks for this data cleaning run.
Dataset: {len(df_original)} rows before, {len(df_cleaned)} rows after.
Initial Score: {initial_score} -> Final Score: {final_score} (Delta: {score_delta:+g} points).

Transformations Executed:
{json.dumps(logs[-10:], indent=2)}

Remaining Unresolved Issues:
{json.dumps(remaining_issues, indent=2)}

Ground your explanations STRICTLY in the actions above. Do not fabricate columns or operations.
"""

    narrative = NarrativeReport(
        executive_summary=f"Cleaned dataset from initial quality score of {initial_score} to {final_score} (+{score_delta} points). Resolved missing values, duplicates, and type mismatches.",
        decisions_explanation="Executed automated data standardization, imputation, and outlier clipping based on distribution analysis.",
        recommended_manual_checks=[i.get("description", "Inspect remaining anomaly") for i in remaining_issues[:3]],
    )

    try:
        narrative_res = call_llm(
            prompt=prompt,
            response_schema=NarrativeReport,
            system_prompt="You are an explainable AI data reporting agent. Be factual, concise, and professional.",
            run_id=run_id,
            temperature=0.2,
        )
        narrative = narrative_res
    except Exception as e:
        logger.warning(f"[{run_id}] Reporter LLM fallback: {e}")

    total_records_affected = sum(entry.get("records_changed", 0) for entry in logs)

    full_report = {
        "run_id": run_id,
        "dataset_overview": {
            "initial_rows": len(df_original),
            "final_rows": len(df_cleaned),
            "columns": len(df_cleaned.columns),
            "column_names": df_cleaned.columns.tolist(),
        },
        "initial_score": state.get("initial_score", 0.0),
        "final_score": final_score,
        "score_improvement": score_delta,
        "score_components": final_score_obj.components.model_dump(),
        "executive_summary": narrative.executive_summary,
        "decisions_explanation": narrative.decisions_explanation,
        "recommended_manual_checks": narrative.recommended_manual_checks,
        "total_operations": len(logs),
        "total_records_affected": total_records_affected,
        "transformation_log": logs,
        "remaining_issues": remaining_issues,
        "iteration_count": state.get("iteration", 1),
        "charts": chart_paths,
        "downloads": {
            "csv": str(csv_path),
            "xlsx": str(xlsx_path),
        },
    }

    # Save to MongoDB
    repo.save_report(run_id, full_report)
    repo.update_run(run_id, {
        "status": RunStatus.COMPLETED.value,
        "current_stage": "done",
        "initial_score": initial_score,
        "final_score": final_score,
        "score_improvement": score_delta,
        "iteration": state.get("iteration", 1),
    })

    logger.info(f"[{run_id}] Reporter Node complete. Report saved to DB and disk.")

    return {
        "report": full_report,
        "final_score": final_score,
        "status": RunStatus.COMPLETED.value,
    }

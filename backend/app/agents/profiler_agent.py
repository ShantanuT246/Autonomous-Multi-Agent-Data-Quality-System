import logging
from typing import Any, Dict
from backend.app.db.repository import repo
from backend.app.graph.state import CleaningState, load_dataframe_ref
from backend.app.reports.quality_score import compute_quality_score
from backend.app.schemas.enums import RunStatus
from backend.app.tools.profile import profile_dataset_extended

logger = logging.getLogger(__name__)


def profiler_node(state: CleaningState) -> Dict[str, Any]:
    """
    Profiler Agent:
    - Analyzes the current DataFrame copy
    - Computes data quality metrics and score
    - Saves initial_profile on iteration 0, current_profile on all iterations
    """
    run_id = state.get("run_id", "default_run")
    iteration = state.get("iteration", 0)
    current_ref = state.get("current_df_ref") or state.get("original_df_ref")

    if not current_ref:
        raise ValueError("No DataFrame reference available for profiler node.")

    df = load_dataframe_ref(current_ref)
    
    repo.add_pipeline_log(
        run_id=run_id,
        stage="profiler",
        level="INFO",
        message=f"[Iteration {iteration}] Profiling dataset: {len(df)} rows, {len(df.columns)} columns ({', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}).",
    )

    profile = profile_dataset_extended(df)
    score_obj = compute_quality_score(df)
    score = score_obj.total

    repo.add_pipeline_log(
        run_id=run_id,
        stage="profiler",
        level="INFO",
        message=f"Dimension health breakdown: Completeness {score_obj.components.completeness:.1f}%, Uniqueness {score_obj.components.uniqueness:.1f}%, Validity {score_obj.components.validity:.1f}%, Consistency {score_obj.components.consistency:.1f}%, Type correctness {score_obj.components.type_correctness:.1f}%, Outlier ratio {score_obj.components.outlier_ratio:.1f}%.",
    )

    repo.add_pipeline_log(
        run_id=run_id,
        stage="profiler",
        level="SUCCESS",
        message=f"Quality Score established at {score:.1f} / 100.0 (Iteration {iteration}).",
    )

    logger.info(f"[{run_id}] Profiler Node complete. Iteration {iteration}, Quality Score: {score}")

    updates: Dict[str, Any] = {
        "current_profile": profile,
        "current_score": score,
        "status": RunStatus.PROFILING.value,
    }

    if iteration == 0 or "initial_profile" not in state:
        updates["initial_profile"] = profile
        updates["initial_score"] = score
        updates["best_score"] = score
        updates["best_df_ref"] = current_ref

    return updates

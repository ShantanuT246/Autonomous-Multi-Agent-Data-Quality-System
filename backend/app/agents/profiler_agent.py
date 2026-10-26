import logging
from typing import Any, Dict
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
    profile = profile_dataset_extended(df)
    score_obj = compute_quality_score(df)
    score = score_obj.total

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

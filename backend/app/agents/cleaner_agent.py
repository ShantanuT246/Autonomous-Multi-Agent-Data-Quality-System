import logging
from typing import Any, Dict, List
import pandas as pd
from backend.app.db.repository import repo
from backend.app.graph.state import (
    CleaningState,
    load_dataframe_ref,
    save_dataframe_ref,
)
from backend.app.schemas.enums import RunStatus
from backend.app.schemas.models import LogEntry, PlannedAction
from backend.app.tools.registry import execute_tool_safely

logger = logging.getLogger(__name__)


def cleaner_node(state: CleaningState) -> Dict[str, Any]:
    """
    Data Cleaning Agent (Executor):
    - Loops sequentially over the planned actions.
    - Dispatches to the deterministic tool registry.
    - Wraps every execution safely; collects transformation logs.
    - Persists an immutable snapshot of the cleaned DataFrame per iteration.
    """
    run_id = state.get("run_id", "default_run")
    iteration = state.get("iteration", 0) + 1
    current_ref = state.get("current_df_ref") or state.get("original_df_ref")

    df: pd.DataFrame = load_dataframe_ref(current_ref)
    plan_data = state.get("cleaning_plan", [])
    actions = [PlannedAction.model_validate(p) for p in plan_data]

    execution_log: List[Dict[str, Any]] = list(state.get("execution_log", []))

    repo.add_pipeline_log(
        run_id=run_id,
        stage="cleaner",
        level="INFO",
        message=f"[Iteration {iteration}] Cleaner Agent dispatching {len(actions)} deterministic operations...",
    )

    logger.info(f"[{run_id}] Cleaner Node executing {len(actions)} actions for Iteration {iteration}...")

    for idx, act in enumerate(actions, 1):
        act_name = act.action.value if hasattr(act.action, "value") else str(act.action)
        df, log_entry = execute_tool_safely(
            action=act_name,
            df=df,
            column=act.column,
            params=act.params,
        )
        execution_log.append(log_entry.model_dump())

        target_desc = f"'{act.column}'" if act.column else "entire dataset"
        repo.add_pipeline_log(
            run_id=run_id,
            stage="cleaner",
            level="ACTION",
            message=f"[{idx}/{len(actions)}] Executed {act_name} on {target_desc}: {log_entry.details or 'Applied successfully'}.",
            details={
                "column": act.column,
                "action": act_name,
                "records_changed": log_entry.records_changed,
                "before_sample": str(log_entry.before_sample) if log_entry.before_sample is not None else None,
                "after_sample": str(log_entry.after_sample) if log_entry.after_sample is not None else None,
            },
        )

    # Save snapshot of the cleaned dataframe for this iteration
    new_snapshot_ref = save_dataframe_ref(df, run_id, f"iteration_{iteration}")

    repo.add_pipeline_log(
        run_id=run_id,
        stage="cleaner",
        level="SUCCESS",
        message=f"Cleaner finished applying transformations. Snapshot iteration_{iteration} committed ({len(df)} rows).",
    )

    logger.info(f"[{run_id}] Cleaner Node complete. Snapshot saved to {new_snapshot_ref}.")

    return {
        "current_df_ref": new_snapshot_ref,
        "execution_log": execution_log,
        "iteration": iteration,
        "status": RunStatus.CLEANING.value,
    }

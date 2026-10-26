import logging
from typing import Any, Callable, Dict, Optional, Tuple
import pandas as pd
from backend.app.config import settings
from backend.app.schemas.enums import ActionType
from backend.app.schemas.models import LogEntry
from backend.app.tools.categories import standardize_categories
from backend.app.tools.duplicates import drop_duplicates
from backend.app.tools.dtypes import cast_dtype, parse_dates
from backend.app.tools.impute import (
    fill_unknown,
    impute_constant,
    impute_knn,
    impute_mean,
    impute_median,
    impute_mode,
)
from backend.app.tools.outliers import clip_outliers
from backend.app.tools.review import flag_for_review, no_action
from backend.app.tools.sanity import convert_units, drop_rows, set_null_invalid
from backend.app.tools.text import normalize_case, strip_whitespace

logger = logging.getLogger(__name__)

# Canonical tool dispatch registry
TOOL_REGISTRY: Dict[str, Callable[..., Tuple[pd.DataFrame, LogEntry]]] = {
    ActionType.IMPUTE_MEDIAN.value: impute_median,
    ActionType.IMPUTE_MEAN.value: impute_mean,
    ActionType.IMPUTE_MODE.value: impute_mode,
    ActionType.IMPUTE_CONSTANT.value: impute_constant,
    ActionType.IMPUTE_KNN.value: impute_knn,
    ActionType.FILL_UNKNOWN.value: fill_unknown,
    ActionType.DROP_DUPLICATES.value: drop_duplicates,
    ActionType.STANDARDIZE_CATEGORIES.value: standardize_categories,
    ActionType.CAST_DTYPE.value: cast_dtype,
    ActionType.PARSE_DATES.value: parse_dates,
    ActionType.CLIP_OUTLIERS.value: clip_outliers,
    ActionType.SET_NULL_INVALID.value: set_null_invalid,
    ActionType.DROP_ROWS.value: drop_rows,
    ActionType.STRIP_WHITESPACE.value: strip_whitespace,
    ActionType.NORMALIZE_CASE.value: normalize_case,
    ActionType.CONVERT_UNITS.value: convert_units,
    ActionType.FLAG_FOR_REVIEW.value: flag_for_review,
    ActionType.NO_ACTION.value: no_action,
}


def execute_tool_safely(
    action: str,
    df: pd.DataFrame,
    column: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    max_row_loss_ratio: Optional[float] = None,
) -> Tuple[pd.DataFrame, LogEntry]:
    """
    Safely dispatches and executes a tool from the registry.
    Enforces:
    1. Operates strictly on a deep copy of the DataFrame.
    2. Exception catching: failure logs as 'failed' status without crashing pipeline.
    3. Row-loss guard: blocks transformations exceeding threshold (e.g. 20% row deletion).
    """
    if params is None:
        params = {}

    if max_row_loss_ratio is None:
        max_row_loss_ratio = settings.MAX_ROW_LOSS_RATIO

    action_key = str(action).lower().strip()
    tool_func = TOOL_REGISTRY.get(action_key)

    if not tool_func:
        logger.warning(f"Tool '{action}' not found in registry.")
        return df, LogEntry(
            column=column,
            issue="unknown_tool",
            action=action,
            records_changed=0,
            status="failed",
            details=f"Tool '{action}' is not registered in the system.",
        )

    initial_row_count = len(df)
    df_copy = df.copy(deep=True)

    try:
        # Pass column if supported and provided
        call_kwargs = dict(params)
        if column:
            call_kwargs["column"] = column

        result_df, log_entry = tool_func(df_copy, **call_kwargs)

        # Check Row-loss Guardrail
        final_row_count = len(result_df)
        if initial_row_count > 0:
            row_loss_ratio = (initial_row_count - final_row_count) / initial_row_count
            if row_loss_ratio > max_row_loss_ratio:
                logger.warning(
                    f"Action '{action}' blocked by Row-loss Guard: Would drop "
                    f"{initial_row_count - final_row_count} rows ({round(row_loss_ratio*100, 1)}%), "
                    f"exceeding max limit of {int(max_row_loss_ratio*100)}%."
                )
                return df, LogEntry(
                    column=column,
                    issue="row_loss_guard_triggered",
                    action="flag_for_review",
                    records_changed=0,
                    status="blocked",
                    details=(
                        f"Action blocked by safety guardrail: Attempted to drop "
                        f"{initial_row_count - final_row_count} rows ({round(row_loss_ratio*100, 1)}%). "
                        f"Escalated to manual review."
                    ),
                )

        return result_df, log_entry

    except Exception as e:
        logger.exception(f"Error executing tool '{action}': {e}")
        return df, LogEntry(
            column=column,
            issue="tool_execution_error",
            action=action,
            records_changed=0,
            status="failed",
            details=f"Exception during tool execution: {str(e)}",
        )

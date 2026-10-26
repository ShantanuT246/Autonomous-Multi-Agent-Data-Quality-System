from typing import Optional, Tuple
import pandas as pd
from backend.app.schemas.models import LogEntry


def flag_for_review(
    df: pd.DataFrame,
    column: Optional[str] = None,
    reason: str = "Flagged for manual review",
    **kwargs,
) -> Tuple[pd.DataFrame, LogEntry]:
    """
    Does not modify data; creates an audit log entry for human-in-the-loop review.
    """
    return df, LogEntry(
        column=column,
        issue="ambiguous_data",
        action="flag_for_review",
        records_changed=0,
        status="flagged",
        details=reason,
    )


def no_action(
    df: pd.DataFrame,
    column: Optional[str] = None,
    reason: str = "No action necessary",
    **kwargs,
) -> Tuple[pd.DataFrame, LogEntry]:
    """
    Explicitly skips an issue with recorded rationale.
    """
    return df, LogEntry(
        column=column,
        issue="no_action_needed",
        action="no_action",
        records_changed=0,
        status="skipped",
        details=reason,
    )

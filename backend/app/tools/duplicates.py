from typing import List, Optional, Tuple
import pandas as pd
from backend.app.schemas.models import LogEntry


def drop_duplicates(
    df: pd.DataFrame,
    subset: Optional[List[str]] = None,
    keep: str = "first",
    **kwargs,
) -> Tuple[pd.DataFrame, LogEntry]:
    """
    Remove exact duplicate rows (or duplicates on a specific subset of key columns).
    Logs the count of removed records.
    """
    df_copy = df.copy(deep=True)
    initial_rows = len(df_copy)

    # Validate subset columns exist
    if subset:
        valid_subset = [col for col in subset if col in df_copy.columns]
        if not valid_subset:
            valid_subset = None
    else:
        valid_subset = None

    df_cleaned = df_copy.drop_duplicates(subset=valid_subset, keep=keep)
    records_removed = initial_rows - len(df_cleaned)

    col_name = ", ".join(valid_subset) if valid_subset else "All Columns"

    return df_cleaned, LogEntry(
        column=col_name,
        issue="duplicate_rows",
        action="drop_duplicates",
        records_changed=records_removed,
        before_sample=f"{initial_rows} rows",
        after_sample=f"{len(df_cleaned)} rows",
        status="success" if records_removed > 0 else "skipped",
        details=f"Dropped {records_removed} duplicate rows (subset={col_name})",
    )
